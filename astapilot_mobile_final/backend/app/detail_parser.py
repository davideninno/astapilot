from __future__ import annotations
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .ingestion_models import AuctionCandidate, AuctionDocument, PipelineStatus

MONEY_RE = re.compile(r"(?:€|EUR|euro)?\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{1,2})|[0-9]+(?:[.,][0-9]{1,2})?)", re.I)
DATE_RE = re.compile(r"\b([0-3]?\d)[/.-]([01]?\d)[/.-](20\d{2})\b")
TIME_RE = re.compile(r"\b([0-2]?\d)[:.]([0-5]\d)\b")
SURFACE_RE = re.compile(r"(?:superficie(?:\s+commerciale)?|mq|m²)\s*[:\-]?\s*([0-9]+(?:[.,][0-9]+)?)", re.I)
PROVINCE_RE = re.compile(r"\(([A-Z]{2})\)")


def _money_near(text: str, labels: tuple[str, ...]) -> float | None:
    low = text.lower()
    for label in labels:
        pos = low.find(label.lower())
        if pos < 0:
            continue
        chunk = text[pos:pos + 220]
        m = MONEY_RE.search(chunk)
        if not m:
            continue
        raw = m.group(1).replace(".", "").replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            pass
    return None


def _date_near(text: str, labels: tuple[str, ...]) -> datetime | None:
    low = text.lower()
    for label in labels:
        pos = low.find(label.lower())
        if pos < 0:
            continue
        chunk = text[pos:pos + 260]
        dm = DATE_RE.search(chunk)
        if not dm:
            continue
        d, m, y = [int(x) for x in dm.groups()]
        tm = TIME_RE.search(chunk)
        hh, mm = (int(tm.group(1)), int(tm.group(2))) if tm else (0, 0)
        try:
            return datetime(y, m, d, hh, mm)
        except ValueError:
            pass
    return None


def _capture(patterns: tuple[str, ...], text: str) -> str | None:
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip(" :-,.;")
    return None


def _classify_document(label: str, href: str) -> str:
    s = f"{label} {href}".lower()
    if any(k in s for k in ("perizia", "relazione di stima", "stima", "expert")):
        return "APPRAISAL"
    if any(k in s for k in ("avviso", "notice")):
        return "SALE_NOTICE"
    if any(k in s for k in ("ordinanza", "order")):
        return "SALE_ORDER"
    if any(k in s for k in ("planimetr", "floorplan")):
        return "FLOOR_PLAN"
    if "foto" in s or "photo" in s:
        return "PHOTO"
    return "OTHER"


def parse_detail(candidate: AuctionCandidate, html: str) -> tuple[AuctionCandidate, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(" ", strip=True) or title
    text = soup.get_text("\n", strip=True)
    compact = re.sub(r"[ \t]+", " ", text)

    candidate.title = candidate.title or title
    candidate.base_price = candidate.base_price or _money_near(compact, ("prezzo base", "base d'asta", "base asta", "prezzo d'asta"))
    candidate.minimum_bid = candidate.minimum_bid or _money_near(compact, ("offerta minima", "offerta min", "minimum bid"))
    candidate.minimum_raise = candidate.minimum_raise or _money_near(compact, ("rilancio minimo", "rialzo minimo", "minimum raise"))
    candidate.auction_date = candidate.auction_date or _date_near(compact, ("data asta", "data vendita", "vendita il", "asta il"))
    candidate.bid_deadline = candidate.bid_deadline or _date_near(compact, ("termine offerte", "scadenza offerte", "presentazione offerte", "offerte entro"))

    candidate.court = candidate.court or _capture((
        r"Tribunale\s+di\s+([^\n|]{2,80})",
        r"Tribunale\s*[:\-]\s*([^\n|]{2,80})",
    ), text)
    candidate.procedure_number = candidate.procedure_number or _capture((
        r"(?:R\.?G\.?E\.?|procedura(?:\s+esecutiva)?(?:\s+immobiliare)?)\s*(?:n\.?|nr\.?|:)??\s*([0-9]+\s*/\s*20[0-9]{2})",
    ), text)
    candidate.lot_number = candidate.lot_number or _capture((
        r"Lotto\s*(?:n\.?|nr\.?|:)??\s*([A-Za-z0-9-]+)",
    ), text)
    candidate.address = candidate.address or _capture((
        r"(?:indirizzo|ubicazione)\s*[:\-]\s*([^\n]{5,160})",
        r"\b((?:Via|Viale|Piazza|Corso|Vicolo|Localit[aà]|Strada)\s+[^\n,]{3,100}(?:,\s*\d+[A-Za-z/]*)?)",
    ), text)
    candidate.property_type = candidate.property_type or _capture((
        r"(?:tipologia|categoria immobile)\s*[:\-]\s*([^\n]{3,80})",
    ), text)
    if candidate.surface_sqm is None:
        sm = SURFACE_RE.search(compact)
        if sm:
            try:
                candidate.surface_sqm = float(sm.group(1).replace(",", "."))
            except ValueError:
                pass
    if not candidate.province:
        pm = PROVINCE_RE.search(candidate.address or compact[:1200])
        if pm:
            candidate.province = pm.group(1)
    if not candidate.city:
        city = _capture((
            r"(?:comune|citt[aà])\s*[:\-]\s*([^\n,|]{2,80})",
            r"(?:ubicazione|indirizzo)\s*[:\-][^\n]{0,140},\s*([^\n,(]{2,70})\s*\([A-Z]{2}\)",
        ), text)
        candidate.city = city
    candidate.description = candidate.description or compact[:2500]

    docs: list[AuctionDocument] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(candidate.source_url, a["href"].strip())
        label = a.get_text(" ", strip=True)
        low = f"{label} {href}".lower()
        path = urlparse(href).path.lower()
        is_doc = path.endswith((".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png")) or any(
            k in low for k in ("perizia", "avviso", "ordinanza", "planimetr", "relazione di stima")
        )
        if not is_doc or href in seen:
            continue
        seen.add(href)
        docs.append(AuctionDocument(url=href, title=label or None, document_type=_classify_document(label, href)))
    candidate.documents = docs
    candidate.pipeline_status = PipelineStatus.DETAIL_FETCHED
    return candidate, compact
