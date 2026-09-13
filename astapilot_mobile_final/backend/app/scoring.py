from __future__ import annotations
from .models import (
    AuctionAnalysisInput,
    AuctionAnalysisResult,
    GateResult,
    Severity,
    ProcedureStatus,
    OwnershipRight,
)

WEIGHTS = {
    "economic": 0.30,
    "urban_planning": 0.20,
    "occupancy": 0.15,
    "documentation": 0.15,
    "procedure": 0.10,
    "marketability": 0.10,
}

SEVERITY_DEFAULT_CAP = {
    Severity.C1: 100,
    Severity.C2: 84,
    Severity.C3: 69,
    Severity.C4: 25,
}

BLOCKING_PROCEDURE_STATUSES = {
    ProcedureStatus.SUSPENDED,
    ProcedureStatus.CANCELLED,
    ProcedureStatus.REVOKED,
    ProcedureStatus.ADJUDICATED,
}


def _procedure_gate(data: AuctionAnalysisInput) -> GateResult:
    if data.procedure_status in BLOCKING_PROCEDURE_STATUSES:
        return GateResult(
            blocked=True,
            reason=f"Procedura non attiva: {data.procedure_status.value}",
        )
    return GateResult(blocked=False)


def _rights_gate(data: AuctionAnalysisInput) -> GateResult:
    if data.user_goal == "HOME" and data.ownership_right != OwnershipRight.FULL_OWNERSHIP:
        return GateResult(
            blocked=True,
            reason=(
                f"Diritto acquistato incompatibile con uso abitativo immediato: "
                f"{data.ownership_right.value}"
            ),
        )
    return GateResult(blocked=False)


def _raw_score(data: AuctionAnalysisInput) -> float:
    s = data.component_scores
    return (
        s.economic * WEIGHTS["economic"]
        + s.urban_planning * WEIGHTS["urban_planning"]
        + s.occupancy * WEIGHTS["occupancy"]
        + s.documentation * WEIGHTS["documentation"]
        + s.procedure * WEIGHTS["procedure"]
        + s.marketability * WEIGHTS["marketability"]
    )


def _confidence_score(data: AuctionAnalysisInput) -> int:
    c = data.confidence_inputs
    score = (
        c.document_coverage * 0.40
        + c.extraction_confidence * 0.30
        + c.cross_document_consistency * 0.20
        + c.data_freshness * 0.10
    )
    return round(score)


def _score_cap(data: AuctionAnalysisInput) -> int:
    if not data.risks:
        return 100

    caps = []
    c3_count = 0
    for risk in data.risks:
        if risk.severity == Severity.C3:
            c3_count += 1
        cap = risk.score_cap if risk.score_cap is not None else SEVERITY_DEFAULT_CAP[risk.severity]
        caps.append(cap)

    cap = min(caps) if caps else 100
    if c3_count >= 2:
        cap = min(cap, 49)
    return cap


def _profile(score: int | None, blocked: bool, critical: bool, confidence: int) -> str:
    if blocked:
        return "BLOCKED"
    if score is None:
        return "UNRATED"
    if critical or score <= 25:
        return "CRITICAL"
    if confidence < 50:
        return "PRELIMINARY"
    if score < 50:
        return "HIGH_RISK"
    if score < 70:
        return "REVIEW"
    if score < 85:
        return "INTERESTING"
    return "STRONG"


def analyze_auction(data: AuctionAnalysisInput) -> AuctionAnalysisResult:
    procedure_gate = _procedure_gate(data)
    rights_gate = _rights_gate(data)
    blocked = procedure_gate.blocked or rights_gate.blocked
    confidence = _confidence_score(data)
    critical_flags = [r for r in data.risks if r.severity == Severity.C4]

    if blocked:
        reasons = [g.reason for g in (procedure_gate, rights_gate) if g.blocked and g.reason]
        summary = " | ".join(reasons)
        return AuctionAnalysisResult(
            auction_id=data.auction_id,
            title=data.title,
            procedure_gate=procedure_gate,
            rights_gate=rights_gate,
            raw_score=None,
            score_cap=None,
            asta_score=None,
            confidence_score=confidence,
            profile="BLOCKED",
            critical_flags=critical_flags,
            all_risks=data.risks,
            component_scores=data.component_scores,
            decision_summary=summary,
        )

    raw = _raw_score(data)
    cap = _score_cap(data)
    final_score = min(round(raw), cap)
    profile = _profile(final_score, False, bool(critical_flags), confidence)

    if profile == "CRITICAL":
        summary = "Criticità C4 rilevata: verifica professionale necessaria prima di valutare un'offerta."
    elif profile == "HIGH_RISK":
        summary = "Profilo ad alto rischio: approfondire le criticità prima di procedere."
    elif profile == "REVIEW":
        summary = "Opportunità da approfondire: sono presenti elementi che possono incidere sulla decisione."
    elif profile == "PRELIMINARY":
        summary = "Valutazione preliminare: documentazione o affidabilità insufficienti."
    else:
        summary = "Profilo favorevole, fermo restando il controllo delle fonti e dei costi reali."

    return AuctionAnalysisResult(
        auction_id=data.auction_id,
        title=data.title,
        procedure_gate=procedure_gate,
        rights_gate=rights_gate,
        raw_score=round(raw, 2),
        score_cap=cap,
        asta_score=final_score,
        confidence_score=confidence,
        profile=profile,
        critical_flags=critical_flags,
        all_risks=data.risks,
        component_scores=data.component_scores,
        decision_summary=summary,
    )
