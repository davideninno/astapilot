from pathlib import Path

from app.detail_parser import parse_detail
from app.document_analysis import auto_analyze
from app.ingestion_models import AuctionCandidate, AuctionDocument, PipelineStatus


def test_detail_parser_extracts_core_fields_and_documents():
    html = """
    <html><head><title>Asta Napoli</title></head><body>
    <h1>Appartamento in Via Roma 10, Napoli</h1>
    Tribunale di Napoli
    R.G.E. 584/2024 - Lotto 2
    Prezzo base € 185.000,00
    Offerta minima € 138.750,00
    Rilancio minimo € 5.000,00
    Data asta 10/11/2026 ore 15:30
    Termine offerte 09/11/2026 ore 23:59
    <a href="/docs/perizia.pdf">Perizia di stima</a>
    <a href="/docs/avviso.pdf">Avviso di vendita</a>
    </body></html>
    """
    c = AuctionCandidate(source_id="x", source_url="https://example.it/aste/1", fingerprint="abc")
    c, text = parse_detail(c, html)
    assert c.base_price == 185000
    assert c.minimum_bid == 138750
    assert c.minimum_raise == 5000
    assert c.auction_date.year == 2026 and c.auction_date.hour == 15
    assert c.bid_deadline.day == 9
    assert c.procedure_number.replace(" ", "") == "584/2024"
    assert c.lot_number == "2"
    assert {d.document_type for d in c.documents} == {"APPRAISAL", "SALE_NOTICE"}
    assert c.pipeline_status == PipelineStatus.DETAIL_FETCHED


def test_auto_analysis_detects_critical_urban_risk_without_manual_input():
    c = AuctionCandidate(
        source_id="x", source_url="https://example.it/aste/2", fingerprint="critical",
        title="Villino", base_price=185000, minimum_bid=138750,
    )
    text = "L'immobile risulta non sanabile e suscettibile di demolizione. Piena proprietà."
    result = auto_analyze(c, text)
    codes = {r.code for r in result.all_risks}
    assert "URBAN_NON_REMEDIABLE" in codes
    assert "DEMOLITION_RISK" in codes
    assert result.asta_score <= 20
    assert result.profile == "CRITICAL"
    assert c.pipeline_status == PipelineStatus.ANALYZED
