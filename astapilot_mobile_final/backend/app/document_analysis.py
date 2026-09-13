from __future__ import annotations
import re
from pathlib import Path

from .ingestion_models import AuctionCandidate, PipelineStatus
from .models import (
    AuctionAnalysisInput, ComponentScores, ConfidenceInputs, OwnershipRight,
    ProcedureStatus, RiskFactor, SourceRef,
)
from .risk_catalog import RISK_CATALOG
from .scoring import analyze_auction

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


def _extract_pages(path: str) -> list[str]:
    p = Path(path)
    if p.suffix.lower() != ".pdf" or PdfReader is None:
        return []
    try:
        reader = PdfReader(str(p))
        return [(page.extract_text() or "") for page in reader.pages]
    except Exception:
        return []


def _first_regex_hit(pages: list[tuple[str, int, str]], patterns: tuple[str, ...]):
    for doc_name, page_no, text in pages:
        for pat in patterns:
            m = re.search(pat, text, re.I | re.S)
            if m:
                start = max(0, m.start() - 150)
                end = min(len(text), m.end() + 300)
                excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
                return SourceRef(document=doc_name, page=page_no, excerpt=excerpt[:600])
    return None


def _risk(code: str, source: SourceRef | None, confidence: float = 0.90, description: str | None = None) -> RiskFactor:
    base = RISK_CATALOG[code]
    title = code.replace("_", " ").title()
    return RiskFactor(
        code=code, severity=base["severity"], category=base["category"],
        title=title, description=description or title,
        action_required=base.get("action"), score_cap=base.get("score_cap"),
        confidence=confidence, source=source,
    )


def _has(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(p, text, re.I | re.S) for p in patterns)


def _document_coverage(a: AuctionCandidate) -> float:
    types = {d.document_type for d in a.documents if d.local_path}
    weights = {"APPRAISAL": 40, "SALE_NOTICE": 30, "SALE_ORDER": 20, "FLOOR_PLAN": 10}
    return min(100.0, sum(v for k, v in weights.items() if k in types))


def auto_analyze(auction: AuctionCandidate, detail_text: str = ""):
    page_records: list[tuple[str, int, str]] = []
    for doc in auction.documents:
        if not doc.local_path:
            continue
        pages = _extract_pages(doc.local_path)
        if pages:
            doc.pages = len(pages)
            doc.text_extracted = any(len(t.strip()) >= 40 for t in pages)
        for i, text in enumerate(pages, start=1):
            if text.strip():
                page_records.append((doc.title or Path(doc.local_path).name, i, text))

    corpus = detail_text + "\n" + "\n".join(t for _, _, t in page_records)
    low = corpus.lower()
    risks: list[RiskFactor] = []
    seen: set[str] = set()

    # Ordered rules: critical / specific expressions before broader expressions.
    rule_specs = [
        ("URBAN_NON_REMEDIABLE", (r"\bnon\s+(?:è\s+|e'\s+)?sanabil[ei]\b", r"\binsanabil[ei]\b")),
        ("DEMOLITION_RISK", (r"\bordinanza\s+di\s+demolizione\b", r"\bsuscettibil\w*\s+di\s+demolizione\b", r"\bdemolizione\b")),
        ("MUNICIPAL_ACQUISITION_RISK", (r"acquisizion\w*\s+(?:gratuita\s+)?al\s+patrimonio\s+comunale",)),
        ("MAJOR_URBAN_DISCREPANCY", (r"\btotale\s+difformit[aà]\b", r"\babusi?\s+edilizi\w*\b", r"\bdifformit[aà]\s+gravi?\b")),
        ("AGIBILITY_MISSING", (r"\b(?:privo|sprovvisto)\s+(?:del\s+certificato\s+)?di\s+agibilit[aà]\b", r"\bassenza\s+(?:del\s+certificato\s+)?di\s+agibilit[aà]\b")),
        ("TENANCY_OPPOSABLE", (r"\b(?:contratto\s+di\s+)?locazione\s+opponibil\w*\b", r"\bopponibile\s+alla\s+procedura\b")),
        ("TENANCY_NON_OPPOSABLE", (r"\b(?:contratto\s+di\s+)?locazione\s+non\s+opponibil\w*\b", r"\bnon\s+opponibile\s+alla\s+procedura\b")),
        ("OCCUPIED_DEBTOR", (r"\boccupat[oa]\s+(?:dal|dalla)\s+(?:debitore|esecutat[oa])\b",)),
        ("OCCUPIED_THIRD_PARTY", (r"\boccupat[oa]\s+da\s+terz\w*\b",)),
        ("LEGAL_DISPUTE", (r"\bcontenzioso\b", r"\bdomanda\s+giudiziale\b", r"\bgiudizio\s+pendente\b")),
        ("ARCHAEOLOGICAL_CONSTRAINT", (r"\bvincolo\s+archeologic\w*\b", r"\bsoprintendenza\b.{0,80}\barcheologic")),
        ("HERITAGE_CONSTRAINT", (r"\bvincolo\s+(?:storico|paesaggistico|culturale)\b",)),
        ("STRUCTURAL_CRACKS_REPORTED", (r"\blesion\w*\b", r"\bfessurazion\w*\b")),
        ("ASBESTOS_OR_HAZARDOUS_MATERIAL", (r"\bamianto\b", r"\beternit\b")),
        ("CONDO_ARREARS_PRESENT", (r"\barretrat\w*\s+condominial\w*\b", r"\binsolut\w*\s+condominial\w*\b", r"\bspese\s+condominiali\s+non\s+pagate\b")),
        ("RENOVATION_NEEDED", (r"\bda\s+ristrutturare\b", r"\bristrutturazione\s+necessaria\b")),
        ("EASEMENT_OR_SERVITUDE", (r"\bservit[uù]\b",)),
        ("MINOR_CADASTRAL_MISMATCH", (r"\bdifformit[aà]\s+catastal\w*\b", r"\bnon\s+conformit[aà]\s+catastal\w*\b")),
    ]
    for code, patterns in rule_specs:
        src = _first_regex_hit(page_records, patterns)
        if src or _has(patterns, corpus):
            risks.append(_risk(code, src, 0.96 if src else 0.78))
            seen.add(code)

    # A remediable discrepancy must not be inferred from text already classified as non-remediable.
    remed_patterns = (r"\bregolarizzabil\w*\b", r"\bsanabil\w*\b", r"\bregolarizzazione\b")
    if "URBAN_NON_REMEDIABLE" not in seen and _has(remed_patterns, corpus):
        src = _first_regex_hit(page_records, remed_patterns)
        risks.append(_risk("REMEDIABLE_URBAN_DISCREPANCY", src, 0.94 if src else 0.75))
        seen.add("REMEDIABLE_URBAN_DISCREPANCY")

    # Rights / procedure gates.
    ownership = OwnershipRight.FULL_OWNERSHIP
    if re.search(r"\bnuda\s+propriet[aà]\b", low):
        ownership = OwnershipRight.BARE_OWNERSHIP
        risks.append(_risk("BARE_OWNERSHIP", _first_regex_hit(page_records, (r"\bnuda\s+propriet[aà]\b",)), 0.98))
    elif "usufrutto" in low and "piena proprietà" not in low and "piena proprieta" not in low:
        ownership = OwnershipRight.USUFRUCT
        risks.append(_risk("USUFRUCT_ONLY", _first_regex_hit(page_records, (r"\busufrutto\b",)), 0.90))
    elif re.search(r"\bquota\s+(?:di\s+)?propriet[aà]\b", low):
        ownership = OwnershipRight.OWNERSHIP_SHARE
        risks.append(_risk("OWNERSHIP_SHARE", _first_regex_hit(page_records, (r"\bquota\s+(?:di\s+)?propriet[aà]\b",)), 0.94))

    proc = ProcedureStatus.ACTIVE
    if re.search(r"\b(?:procedura|vendita|asta)\s+sospes[ao]\b", low):
        proc = ProcedureStatus.SUSPENDED
    elif re.search(r"\b(?:vendita|procedura)\s+revocat[ao]\b", low):
        proc = ProcedureStatus.REVOKED
    elif re.search(r"\b(?:asta|vendita)\s+annullat[ao]\b", low):
        proc = ProcedureStatus.CANCELLED
    elif re.search(r"\baggiudicat[oa]\b", low) and "non aggiudicat" not in low:
        proc = ProcedureStatus.ADJUDICATED

    # Conservative component scores derived from facts, never from a free-form LLM judgment.
    urban = 100.0
    occupancy = 100.0
    marketability = 75.0
    for r in risks:
        if r.code in {"URBAN_NON_REMEDIABLE", "DEMOLITION_RISK", "MUNICIPAL_ACQUISITION_RISK"}:
            urban = min(urban, 5)
        elif r.code == "MAJOR_URBAN_DISCREPANCY":
            urban = min(urban, 35)
        elif r.code == "REMEDIABLE_URBAN_DISCREPANCY":
            urban = min(urban, 70)
        elif r.code == "AGIBILITY_MISSING":
            urban = min(urban, 55)
        if r.code == "TENANCY_OPPOSABLE":
            occupancy = min(occupancy, 35)
        elif r.code == "OCCUPIED_THIRD_PARTY":
            occupancy = min(occupancy, 45)
        elif r.code in {"TENANCY_NON_OPPOSABLE", "OCCUPIED_DEBTOR"}:
            occupancy = min(occupancy, 65)
        if r.code in {"LEGAL_DISPUTE", "DEMOLITION_RISK", "URBAN_NON_REMEDIABLE"}:
            marketability = min(marketability, 25)

    coverage = _document_coverage(auction)
    documentation = coverage
    if not any(d.document_type == "APPRAISAL" and d.local_path for d in auction.documents):
        if "KEY_DOCUMENT_MISSING" not in seen:
            risks.append(_risk("KEY_DOCUMENT_MISSING", None, 1.0, "Perizia di stima non disponibile o non scaricata."))
        documentation = min(documentation, 55)

    procedure = 100.0
    for val in (auction.minimum_bid, auction.auction_date, auction.bid_deadline):
        if val is None:
            procedure -= 15
    if proc != ProcedureStatus.ACTIVE:
        procedure = 0

    extraction_conf = 92.0 if page_records else 58.0
    consistency = 94.0
    if auction.surface_sqm and auction.surface_sqm <= 0:
        consistency = 60.0
        risks.append(_risk("DOCUMENT_CONTRADICTION", None, 0.8))

    data = AuctionAnalysisInput(
        auction_id=auction.fingerprint or auction.source_url,
        title=auction.title or auction.address or "Asta immobiliare",
        procedure_status=proc,
        ownership_right=ownership,
        component_scores=ComponentScores(
            economic=50.0,  # valuation engine fills this later
            urban_planning=urban,
            occupancy=occupancy,
            documentation=documentation,
            procedure=max(0.0, procedure),
            marketability=marketability,
        ),
        confidence_inputs=ConfidenceInputs(
            document_coverage=coverage,
            extraction_confidence=extraction_conf,
            cross_document_consistency=consistency,
            data_freshness=95.0,
        ),
        risks=risks,
    )
    result = analyze_auction(data)
    auction.pipeline_status = PipelineStatus.ANALYZED
    auction.analysis_id = data.auction_id
    return result
