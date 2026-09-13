from __future__ import annotations
from .ingestion_models import AuctionCandidate


def compute_quality_score(a: AuctionCandidate) -> int:
    fields = {
        "court": 8, "procedure_number": 10, "lot_number": 4, "address": 10,
        "base_price": 8, "minimum_bid": 10, "auction_date": 10, "bid_deadline": 8,
        "property_type": 5, "description": 5, "surface_sqm": 5,
    }
    score = sum(weight for name, weight in fields.items() if getattr(a, name, None) not in (None, ""))
    doc_types = {d.document_type for d in a.documents}
    if "APPRAISAL" in doc_types:
        score += 5
    if "SALE_NOTICE" in doc_types:
        score += 5
    if "SALE_ORDER" in doc_types:
        score += 3
    if any(d.local_path for d in a.documents):
        score += 4
    return min(100, score)
