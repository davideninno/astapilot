from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from .time_utils import utcnow_naive


class SourceKind(str, Enum):
    OFFICIAL = "OFFICIAL"
    AUTHORIZED_PUBLISHER = "AUTHORIZED_PUBLISHER"
    OTHER = "OTHER"


class PipelineStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    DETAIL_FETCHED = "DETAIL_FETCHED"
    DOCUMENTS_DOWNLOADED = "DOCUMENTS_DOWNLOADED"
    ANALYZED = "ANALYZED"
    STALE = "STALE"
    FAILED = "FAILED"


class AuctionSource(BaseModel):
    id: str
    name: str
    base_url: str
    kind: SourceKind
    enabled: bool = True
    coverage: str = "ITALY"
    adapter: str = "generic_sitemap"
    last_success_at: Optional[datetime] = None
    last_checked_at: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    health: str = "UNKNOWN"
    last_discovered_count: int = 0


class AuctionDocument(BaseModel):
    url: str
    title: Optional[str] = None
    document_type: str = "OTHER"
    local_path: Optional[str] = None
    content_type: Optional[str] = None
    pages: Optional[int] = None
    text_extracted: bool = False
    sha256: Optional[str] = None
    bytes: Optional[int] = None
    downloaded_at: Optional[datetime] = None
    version: int = 1


class AuctionCandidate(BaseModel):
    source_id: str
    source_url: str
    source_urls: list[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=utcnow_naive)
    last_seen_at: datetime = Field(default_factory=utcnow_naive)
    last_refreshed_at: Optional[datetime] = None
    external_id: Optional[str] = None
    canonical_id: Optional[str] = None
    title: Optional[str] = None
    court: Optional[str] = None
    procedure_number: Optional[str] = None
    lot_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    base_price: Optional[float] = None
    minimum_bid: Optional[float] = None
    minimum_raise: Optional[float] = None
    auction_date: Optional[datetime] = None
    bid_deadline: Optional[datetime] = None
    property_type: Optional[str] = None
    surface_sqm: Optional[float] = None
    rooms: Optional[float] = None
    occupancy_hint: Optional[str] = None
    description: Optional[str] = None
    documents: list[AuctionDocument] = Field(default_factory=list)
    fingerprint: Optional[str] = None
    pipeline_status: PipelineStatus = PipelineStatus.DISCOVERED
    analysis_id: Optional[str] = None
    last_error: Optional[str] = None
    quality_score: int = 0
    needs_refresh: bool = True


class IngestionStats(BaseModel):
    started_at: datetime
    finished_at: Optional[datetime] = None
    sources_seen: int = 0
    sources_ok: int = 0
    sources_failed: int = 0
    candidates_found: int = 0
    candidates_new: int = 0
    candidates_updated: int = 0
    details_fetched: int = 0
    documents_downloaded: int = 0
    documents_unchanged: int = 0
    auctions_analyzed: int = 0
    duplicates: int = 0
    queue_due: int = 0
    queue_processed: int = 0
    errors: list[str] = Field(default_factory=list)


class IngestionStatus(BaseModel):
    running: bool = False
    last_run: Optional[IngestionStats] = None
    total_candidates: int = 0
    source_count: int = 0
    analyzed_count: int = 0
    healthy_sources: int = 0
    degraded_sources: int = 0
    failed_sources: int = 0
    due_refresh_count: int = 0
