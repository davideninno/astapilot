from __future__ import annotations
import hashlib
import re
from .ingestion_models import AuctionCandidate


def _norm(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower().strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^a-z0-9àèéìòù/ -]+", "", value)
    return value


def canonical_key(candidate: AuctionCandidate) -> str:
    """Cross-publisher identity. Court + procedure + lot is preferred.
    Falls back to stable property/date attributes when procedural identity is unavailable.
    """
    court = _norm(candidate.court)
    proc = _norm(candidate.procedure_number).replace(" ", "")
    lot = _norm(candidate.lot_number) or "1"
    if court and proc:
        return f"court:{court}|proc:{proc}|lot:{lot}"

    address = _norm(candidate.address)
    auction_day = candidate.auction_date.date().isoformat() if candidate.auction_date else ""
    minimum = f"{candidate.minimum_bid:.2f}" if candidate.minimum_bid is not None else ""
    if address and (auction_day or minimum):
        return f"addr:{address}|date:{auction_day}|min:{minimum}"

    return f"url:{candidate.source_url.split('?')[0].lower()}"


def fingerprint(candidate: AuctionCandidate) -> str:
    key = canonical_key(candidate)
    candidate.canonical_id = key
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
