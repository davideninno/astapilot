import asyncio
import httpx

from app.ingestion import MinistrySourceDirectoryAdapter, GenericSitemapAdapter, IngestionService, _fingerprint
from app.ingestion_models import AuctionSource, SourceKind, AuctionCandidate


def test_ministry_directory_extracts_authorized_sites():
    async def run():
        html = """
        <html><body>
        www.asteflorio.it www.case-asta.it
        <a href="https://www.aggiudicato.io/foo">x</a>
        </body></html>
        """
        def handler(request):
            return httpx.Response(200, text=html)
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await MinistrySourceDirectoryAdapter().discover_sources(client)
    sources = asyncio.run(run())
    domains = {s.base_url for s in sources}
    assert "https://www.asteflorio.it" in domains
    assert "https://www.case-asta.it" in domains
    assert "https://www.aggiudicato.io" in domains
    assert any(s.id == "pvp-official" for s in sources)


def test_sitemap_discovers_only_likely_auction_urls():
    async def run():
        sitemap = """<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://example.it/aste/lotto-123</loc></url>
        <url><loc>https://example.it/chi-siamo</loc></url>
        <url><loc>https://example.it/vendita/immobile-456</loc></url>
        </urlset>"""
        def handler(request):
            if request.url.path == "/sitemap.xml":
                return httpx.Response(200, text=sitemap, headers={"content-type": "application/xml"})
            return httpx.Response(404)
        transport = httpx.MockTransport(handler)
        source = AuctionSource(id="x", name="Example", base_url="https://example.it", kind=SourceKind.AUTHORIZED_PUBLISHER)
        async with httpx.AsyncClient(transport=transport) as client:
            return await GenericSitemapAdapter().discover(client, source)
    found = asyncio.run(run())
    assert len(found) == 2
    assert all(c.fingerprint for c in found)
    assert all("chi-siamo" not in c.source_url for c in found)


def test_ingestion_is_deduplicated():
    service = IngestionService()
    c = AuctionCandidate(source_id="s", source_url="https://example.it/aste/1")
    c.fingerprint = _fingerprint(c)
    service.candidates[c.fingerprint] = c
    service.candidates[c.fingerprint] = c
    assert len(service.candidates) == 1
