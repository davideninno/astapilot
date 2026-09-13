from datetime import timedelta

from app.ingestion import IngestionService
from app.ingestion_models import AuctionCandidate, PipelineStatus
from app.time_utils import utcnow_naive


def candidate(days=None, refreshed_hours=0, status=PipelineStatus.ANALYZED):
    now = utcnow_naive()
    return AuctionCandidate(
        source_id="test", source_url=f"https://example.test/{days}/{refreshed_hours}/{status}",
        auction_date=(now + timedelta(days=days)) if days is not None else None,
        last_refreshed_at=now - timedelta(hours=refreshed_hours), pipeline_status=status,
    )


def test_refresh_is_more_frequent_near_auction():
    svc = object.__new__(IngestionService)
    assert svc._refresh_interval(candidate(days=1)).total_seconds() == 3600
    assert svc._refresh_interval(candidate(days=5)).total_seconds() == 3 * 3600
    assert svc._refresh_interval(candidate(days=20)).total_seconds() == 12 * 3600
    assert svc._refresh_interval(candidate(days=60)).total_seconds() == 24 * 3600


def test_failed_and_discovered_are_due_immediately():
    svc = object.__new__(IngestionService)
    assert svc._should_refresh(candidate(days=30, status=PipelineStatus.FAILED))
    assert svc._should_refresh(candidate(days=30, status=PipelineStatus.DISCOVERED))


def test_queue_prioritizes_imminent_auctions():
    svc = object.__new__(IngestionService)
    imminent = candidate(days=1, refreshed_hours=2)
    later = candidate(days=50, refreshed_hours=30)
    assert svc._priority(imminent) < svc._priority(later)
