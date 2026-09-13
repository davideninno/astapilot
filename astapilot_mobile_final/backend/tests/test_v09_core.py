from datetime import datetime
from pathlib import Path

from app.identity import fingerprint
from app.ingestion_models import AuctionCandidate
from app.document_analysis import auto_analyze
from app.simulation import SimulationInput, simulate
from app.repository import AuctionRepository


def test_cross_publisher_identity_ignores_source():
    a = AuctionCandidate(source_id="a", source_url="https://a.it/x", court="Napoli", procedure_number="584/2024", lot_number="2")
    b = AuctionCandidate(source_id="b", source_url="https://b.it/y", court="Napoli", procedure_number="584 / 2024", lot_number="2")
    assert fingerprint(a) == fingerprint(b)


def test_non_sanabile_does_not_also_create_remediable_risk():
    c = AuctionCandidate(source_id="x", source_url="https://example.it/x", fingerprint="x")
    r = auto_analyze(c, "L'immobile è non sanabile e suscettibile di demolizione.")
    codes = {x.code for x in r.all_risks}
    assert "URBAN_NON_REMEDIABLE" in codes
    assert "REMEDIABLE_URBAN_DISCREPANCY" not in codes


def test_simulator_personal_limit():
    result = simulate(SimulationInput(
        bid=140000, conservative_market_value=220000, renovation_cost=20000,
        professional_cost=3000, other_costs=2000, contingency_rate=0.05,
        required_margin_rate=0.20,
    ))
    assert result.total_investment > 165000
    assert result.personal_bid_limit < 176000
    assert result.gross_margin > 0


def test_repository_search_filters(tmp_path: Path):
    repo = AuctionRepository(tmp_path / "test.sqlite3")
    a = AuctionCandidate(
        source_id="x", source_url="https://x/1", fingerprint="fp1", canonical_id="c1",
        city="Napoli", province="NA", property_type="Appartamento", minimum_bid=120000,
        auction_date=datetime(2030, 1, 1),
    )
    repo.save_auction(a)
    out = repo.search_auctions(city="Napoli", max_bid=130000, active_after=datetime(2029, 1, 1))
    assert out["total"] == 1
    assert out["items"][0]["fingerprint"] == "fp1"
