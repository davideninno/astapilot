from __future__ import annotations
from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ProcedureStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"
    REVOKED = "REVOKED"
    ADJUDICATED = "ADJUDICATED"


class OwnershipRight(str, Enum):
    FULL_OWNERSHIP = "FULL_OWNERSHIP"
    BARE_OWNERSHIP = "BARE_OWNERSHIP"
    USUFRUCT = "USUFRUCT"
    SURFACE_RIGHT = "SURFACE_RIGHT"
    OWNERSHIP_SHARE = "OWNERSHIP_SHARE"
    OTHER = "OTHER"


class Severity(str, Enum):
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"


class RiskCategory(str, Enum):
    URBAN_PLANNING = "URBAN_PLANNING"
    OCCUPANCY = "OCCUPANCY"
    DOCUMENTATION = "DOCUMENTATION"
    PROCEDURE = "PROCEDURE"
    RIGHTS = "RIGHTS"
    CONDOMINIUM = "CONDOMINIUM"
    PHYSICAL = "PHYSICAL"
    LEGAL = "LEGAL"
    MARKETABILITY = "MARKETABILITY"
    ECONOMIC = "ECONOMIC"


class SourceRef(BaseModel):
    document: str
    page: Optional[int] = None
    excerpt: Optional[str] = None


class RiskFactor(BaseModel):
    code: str
    severity: Severity
    category: RiskCategory
    title: str
    description: str
    action_required: Optional[str] = None
    score_cap: Optional[int] = Field(default=None, ge=0, le=100)
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: Optional[SourceRef] = None


class ComponentScores(BaseModel):
    economic: float = Field(ge=0, le=100)
    urban_planning: float = Field(ge=0, le=100)
    occupancy: float = Field(ge=0, le=100)
    documentation: float = Field(ge=0, le=100)
    procedure: float = Field(ge=0, le=100)
    marketability: float = Field(ge=0, le=100)


class ConfidenceInputs(BaseModel):
    document_coverage: float = Field(ge=0, le=100)
    extraction_confidence: float = Field(ge=0, le=100)
    cross_document_consistency: float = Field(ge=0, le=100)
    data_freshness: float = Field(ge=0, le=100)


class AuctionAnalysisInput(BaseModel):
    auction_id: str
    title: str
    procedure_status: ProcedureStatus = ProcedureStatus.ACTIVE
    ownership_right: OwnershipRight = OwnershipRight.FULL_OWNERSHIP
    user_goal: Literal["HOME", "INVESTMENT", "BOTH"] = "BOTH"
    component_scores: ComponentScores
    confidence_inputs: ConfidenceInputs
    risks: List[RiskFactor] = []


class GateResult(BaseModel):
    blocked: bool
    reason: Optional[str] = None


class AuctionAnalysisResult(BaseModel):
    auction_id: str
    title: str
    procedure_gate: GateResult
    rights_gate: GateResult
    raw_score: Optional[float]
    score_cap: Optional[int]
    asta_score: Optional[int]
    confidence_score: int
    profile: str
    critical_flags: List[RiskFactor]
    all_risks: List[RiskFactor]
    component_scores: ComponentScores
    decision_summary: str
