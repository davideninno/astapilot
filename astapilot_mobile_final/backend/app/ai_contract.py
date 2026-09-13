from __future__ import annotations
from typing import Any, Literal, Protocol
from pydantic import BaseModel, Field


class FactSource(BaseModel):
    document: str
    page: int | None = None
    excerpt: str | None = None


class ExtractedFact(BaseModel):
    key: str
    value: Any = None
    status: Literal["FOUND", "UNKNOWN", "CONFLICT"] = "UNKNOWN"
    confidence: float = Field(default=0.0, ge=0, le=1)
    source: FactSource | None = None


class DocumentExtraction(BaseModel):
    facts: list[ExtractedFact] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    model_version: str | None = None


class StructuredExtractionProvider(Protocol):
    async def extract(self, *, document_name: str, pages: list[str]) -> DocumentExtraction:
        """Provider contract for a JSON-schema constrained LLM extractor.

        Production rule: if a fact is not explicitly supported by the source, return
        UNKNOWN. Legal/technical conclusions must never be invented from absent text.
        """
        ...


CRITICAL_FACT_KEYS = [
    "procedure_status", "ownership_right", "occupancy_status", "lease_opposability",
    "urban_compliance", "sanability", "demolition_risk", "municipal_acquisition_risk",
    "condominium_arrears", "base_price", "minimum_bid", "bid_deadline", "auction_date",
    "deposit", "balance_deadline", "surface_sqm", "appraisal_value",
]
