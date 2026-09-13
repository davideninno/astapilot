from __future__ import annotations
import asyncio
import gzip
import hashlib
import os
import re
import xml.etree.ElementTree as ET
from datetime import timedelta
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .detail_parser import parse_detail
from .document_analysis import auto_analyze
from .document_store import download_documents
from .identity import fingerprint
from .ingestion_models import AuctionSource, AuctionCandidate, IngestionStats, IngestionStatus, SourceKind, PipelineStatus
from .quality import compute_quality_score
from .time_utils import utcnow_naive
from .repository import repository

MINISTRY_DIRECTORY = "https://www.giustizia.it/giustizia/it/mg_1_18.wp"
PVP_URL = "https://pvp.giustizia.it/pvp/"
PROCESS_LIMIT = int(os.getenv("INGESTION_PROCESS_LIMIT", "120"))
SOURCE_CONCURRENCY = int(os.getenv("SOURCE_CONCURRENCY", "6"))
DETAIL_CONCURRENCY = int(os.getenv("DETAIL_CONCURRENCY", "4"))
SITEMAP_CHILD_LIMIT = int(os.getenv("SITEMAP_CHILD_LIMIT", "60"))
SOURCE_PAGE_LIMIT = int(os.getenv("SOURCE_PAGE_LIMIT", "10000"))

AUCTION_URL_HINTS = (
    "asta", "aste", "auction", "vendita", "vendite", "lotto", "immobile",
    "esecuzione", "procedure", "procedura", "annuncio"
)
EXCLUDED_DOMAINS = {"giustizia.it", "www.giustizia.it", "pvp.giustizia.it"}


def _norm_domain(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"^https?://", "", value)
    return value.strip("/ ")


def _source_id(domain: str) -> str:
    return hashlib.sha1(domain.encode("utf-8")).hexdigest()[:12]


def _fingerprint(candidate: AuctionCandidate) -> str:
    """Backward-compatible alias used by the v0.3 test-suite."""
    return fingerprint(candidate)


def _url_discovery_id(url: str) -> str:
    return hashlib.sha256(url.split("#")[0].split("?")[0].lower().encode("utf-8")).hexdigest()


def _refresh_interval(candidate: AuctionCandidate) -> timedelta:
    """Refresh urgent auctions more frequently without hammering every publisher."""
    now = utcnow_naive()
    if candidate.pipeline_status in {PipelineStatus.FAILED, PipelineStatus.DISCOVERED, PipelineStatus.STALE}:
        return timedelta(hours=1)
    if candidate.auction_date:
        days = (candidate.auction_date - now).total_seconds() / 86400
        if days < -2:
            return timedelta(days=3)
        if days <= 2:
            return timedelta(hours=1)
        if days <= 7:
            return timedelta(hours=3)
        if days <= 30:
            return timedelta(hours=6)
    return timedelta(hours=12)


def _queue_priority(candidate: AuctionCandidate) -> tuple:
    now = utcnow_naive()
    new_or_failed = 0 if candidate.pipeline_status in {PipelineStatus.DISCOVERED, PipelineStatus.FAILED, PipelineStatus.STALE} else 1
    if candidate.auction_date:
        seconds = max(0.0, (candidate.auction_date - now).total_seconds())
    else:
        seconds = float("inf")
    refreshed = candidate.last_refreshed_at.timestamp() if candidate.last_refreshed_at else 0.0
    return new_or_failed, seconds, refreshed


class MinistrySourceDirectoryAdapter:
    async def discover_sources(self, client: httpx.AsyncClient) -> list[AuctionSource]:
        sources = [AuctionSource(
            id="pvp-official", name="Portale Vendite Pubbliche", base_url=PVP_URL,
            kind=SourceKind.OFFICIAL, adapter="pvp_authorized_feed",
        )]
        response = await client.get(MINISTRY_DIRECTORY, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        domains: set[str] = set()
        for token in re.findall(r"\b(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", soup.get_text(" ", strip=True)):
            if "." in token and not token.lower().endswith((".pdf", ".jpg", ".png")):
                domains.add(token)
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("http"):
                host = urlparse(href).netloc
                if host:
                    domains.add(host)
        for domain in sorted(domains):
            domain = _norm_domain(domain)
            if domain in EXCLUDED_DOMAINS or domain.endswith("giustizia.it"):
                continue
            sources.append(AuctionSource(
                id=_source_id(domain), name=domain, base_url=f"https://{domain}",
                kind=SourceKind.AUTHORIZED_PUBLISHER, adapter="generic_sitemap",
            ))
        return sources


class GenericSitemapAdapter:
    async def _parse_map(self, client: httpx.AsyncClient, url: str) -> list[str]:
        r = await client.get(url, follow_redirects=True)
        if r.status_code != 200:
            return []
        raw = r.content
        if url.lower().split("?")[0].endswith(".gz") or raw[:2] == b"\x1f\x8b":
            try:
                raw = gzip.decompress(raw)
            except OSError:
                return []
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return []
        return [n.text.strip() for n in root.iter() if n.tag.endswith("loc") and n.text]

    async def _entrypoints(self, client: httpx.AsyncClient, base_url: str) -> list[str]:
        root = base_url.rstrip("/")
        entries = [f"{root}/sitemap.xml", f"{root}/sitemap_index.xml"]
        try:
            r = await client.get(f"{root}/robots.txt", follow_redirects=True)
            if r.status_code == 200:
                for line in r.text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        value = line.split(":", 1)[1].strip()
                        if value.startswith("http"):
                            entries.append(value)
        except Exception:
            pass
        return list(dict.fromkeys(entries))

    async def _sitemap_urls(self, client: httpx.AsyncClient, base_url: str) -> list[str]:
        for entry in await self._entrypoints(client, base_url):
            try:
                locs = await self._parse_map(client, entry)
                if not locs:
                    continue
                child_maps = [u for u in locs if u.lower().split("?")[0].endswith((".xml", ".xml.gz"))][:SITEMAP_CHILD_LIMIT]
                pages = [u for u in locs if u not in child_maps]
                if child_maps:
                    results = await asyncio.gather(*(self._parse_map(client, u) for u in child_maps), return_exceptions=True)
                    for result in results:
                        if isinstance(result, list):
                            pages.extend(result)
                return list(dict.fromkeys(pages))[:SOURCE_PAGE_LIMIT]
            except Exception:
                continue
        return []

    async def discover(self, client: httpx.AsyncClient, source: AuctionSource) -> list[AuctionCandidate]:
        urls = await self._sitemap_urls(client, source.base_url)
        picked: list[AuctionCandidate] = []
        seen: set[str] = set()
        for url in urls:
            low = url.lower()
            if not any(hint in low for hint in AUCTION_URL_HINTS):
                continue
            clean = url.split("#")[0]
            if clean in seen:
                continue
            seen.add(clean)
            picked.append(AuctionCandidate(
                source_id=source.id, source_url=clean, source_urls=[clean],
                fingerprint=_url_discovery_id(clean),
            ))
        return picked


class IngestionService:
    def __init__(self):
        loaded_sources = repository.load_sources()
        self.sources: dict[str, AuctionSource] = {s.id: s for s in loaded_sources}
        if "pvp-official" not in self.sources:
            self.sources["pvp-official"] = AuctionSource(
                id="pvp-official", name="Portale Vendite Pubbliche", base_url=PVP_URL,
                kind=SourceKind.OFFICIAL, adapter="pvp_authorized_feed",
            )
        persisted = repository.load_auction_models()
        self.candidates: dict[str, AuctionCandidate] = {a.fingerprint: a for a in persisted if a.fingerprint}
        self.analyses: dict[str, object] = {}
        self.status = IngestionStatus(source_count=len(self.sources), total_candidates=len(self.candidates))
        self._lock = asyncio.Lock()
        self._directory = MinistrySourceDirectoryAdapter()
        self._generic = GenericSitemapAdapter()
        self._update_status_metrics()

    def _update_status_metrics(self) -> None:
        values = list(self.sources.values())
        self.status.source_count = len(values)
        self.status.total_candidates = len(self.candidates)
        self.status.analyzed_count = sum(c.pipeline_status == PipelineStatus.ANALYZED for c in self.candidates.values())
        self.status.healthy_sources = sum(s.health == "HEALTHY" for s in values)
        self.status.degraded_sources = sum(s.health == "DEGRADED" for s in values)
        self.status.failed_sources = sum(s.health == "FAILED" for s in values)
        self.status.due_refresh_count = sum(self._should_refresh(c) for c in self.candidates.values())

    async def refresh_sources(self, client: httpx.AsyncClient) -> None:
        discovered = await self._directory.discover_sources(client)
        merged: dict[str, AuctionSource] = {}
        for fresh in discovered:
            old = self.sources.get(fresh.id)
            if old:
                fresh.last_success_at = old.last_success_at
                fresh.last_checked_at = old.last_checked_at
                fresh.last_error = old.last_error
                fresh.consecutive_failures = old.consecutive_failures
                fresh.health = old.health
                fresh.last_discovered_count = old.last_discovered_count
                if old.adapter not in {"generic_sitemap", "pvp_authorized_feed"}:
                    fresh.adapter = old.adapter
            merged[fresh.id] = fresh
        for sid, old in self.sources.items():
            if sid not in merged and old.adapter not in {"generic_sitemap", "pvp_authorized_feed"}:
                merged[sid] = old
        self.sources = merged
        for source in self.sources.values():
            repository.save_source(source)
        self._update_status_metrics()

    def _should_refresh(self, candidate: AuctionCandidate) -> bool:
        if not candidate.last_refreshed_at:
            return True
        return utcnow_naive() - candidate.last_refreshed_at >= _refresh_interval(candidate)

    def _merge_canonical(self, incoming: AuctionCandidate) -> tuple[AuctionCandidate, bool]:
        incoming.fingerprint = fingerprint(incoming)
        existing = self.candidates.get(incoming.fingerprint)
        if not existing:
            return incoming, False
        urls = list(dict.fromkeys([*existing.source_urls, existing.source_url, *incoming.source_urls, incoming.source_url]))
        old_docs = {d.url: d for d in existing.documents}
        for doc in incoming.documents:
            if doc.url in old_docs and old_docs[doc.url].sha256:
                prior = old_docs[doc.url]
                doc.sha256, doc.local_path, doc.bytes, doc.downloaded_at, doc.version = (
                    prior.sha256, prior.local_path, prior.bytes, prior.downloaded_at, prior.version
                )
        incoming.source_urls = urls
        incoming.discovered_at = min(existing.discovered_at, incoming.discovered_at)
        incoming.last_seen_at = utcnow_naive()
        return incoming, True

    async def _enrich_and_analyze(self, client: httpx.AsyncClient, candidate: AuctionCandidate, stats: IngestionStats):
        discovery_fp = candidate.fingerprint
        try:
            r = await client.get(candidate.source_url, follow_redirects=True)
            if r.status_code != 200 or "text/html" not in r.headers.get("content-type", "text/html"):
                raise RuntimeError(f"detail http {r.status_code}")
            candidate, detail_text = parse_detail(candidate, r.text)
            candidate, duplicate = self._merge_canonical(candidate)
            if duplicate:
                stats.duplicates += 1
            if discovery_fp and discovery_fp != candidate.fingerprint:
                self.candidates.pop(discovery_fp, None)
            stats.details_fetched += 1
            changed, unchanged = await download_documents(client, candidate)
            stats.documents_downloaded += changed
            stats.documents_unchanged += unchanged
            result = auto_analyze(candidate, detail_text)
            candidate.last_refreshed_at = utcnow_naive()
            candidate.last_seen_at = utcnow_naive()
            candidate.needs_refresh = False
            candidate.quality_score = compute_quality_score(candidate)
            candidate.last_error = None
            stats.auctions_analyzed += 1
            self.candidates[candidate.fingerprint] = candidate
            self.analyses[candidate.fingerprint] = result
            repository.save_auction(candidate, result)
            repository.save_analysis(candidate.fingerprint, result)
        except Exception as exc:
            candidate.last_error = f"{type(exc).__name__}: {exc}"
            candidate.pipeline_status = PipelineStatus.FAILED
            candidate.last_refreshed_at = utcnow_naive()
            candidate.needs_refresh = True
            if candidate.fingerprint:
                self.candidates[candidate.fingerprint] = candidate
                repository.save_auction(candidate)
            stats.errors.append(f"pipeline {candidate.source_url}: {type(exc).__name__}: {exc}")

    async def run_cycle(self) -> IngestionStats:
        if self._lock.locked():
            return self.status.last_run or IngestionStats(started_at=utcnow_naive(), errors=["ingestion already running"])
        async with self._lock:
            self.status.running = True
            stats = IngestionStats(started_at=utcnow_naive())
            timeout = httpx.Timeout(30.0, connect=8.0)
            headers = {"User-Agent": "AstaPilot/1.1 public-auction-indexer; respectful-crawl"}
            discovered_urls = {u for a in self.candidates.values() for u in ([a.source_url] + a.source_urls)}
            queue: list[AuctionCandidate] = []
            try:
                async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
                    try:
                        await self.refresh_sources(client)
                    except Exception as exc:
                        stats.errors.append(f"source directory: {type(exc).__name__}: {exc}")
                    stats.sources_seen = len(self.sources)
                    sem = asyncio.Semaphore(SOURCE_CONCURRENCY)

                    async def one(source: AuctionSource):
                        source.last_checked_at = utcnow_naive()
                        if source.adapter == "pvp_authorized_feed":
                            # Deliberately no guessed/private endpoint. Configure an authorized feed adapter when access is granted.
                            return source.id, [], None
                        try:
                            async with sem:
                                found = await self._generic.discover(client, source)
                            return source.id, found, None
                        except Exception as exc:
                            return source.id, [], f"{type(exc).__name__}: {exc}"

                    results = await asyncio.gather(*(one(s) for s in self.sources.values() if s.enabled))
                    for source_id, found, error in results:
                        source = self.sources[source_id]
                        if error:
                            stats.sources_failed += 1
                            source.last_error = error
                            source.consecutive_failures += 1
                            source.health = "FAILED" if source.consecutive_failures >= 3 else "DEGRADED"
                            stats.errors.append(f"{source_id}: {error}")
                        else:
                            stats.sources_ok += 1
                            source.last_success_at = utcnow_naive()
                            source.last_error = None
                            source.consecutive_failures = 0
                            source.health = "HEALTHY"
                            source.last_discovered_count = len(found)
                            stats.candidates_found += len(found)
                            for candidate in found:
                                if candidate.source_url in discovered_urls:
                                    stats.duplicates += 1
                                    continue
                                discovered_urls.add(candidate.source_url)
                                queue.append(candidate)
                                stats.candidates_new += 1
                        repository.save_source(source)

                    refresh = [a for a in self.candidates.values() if self._should_refresh(a)]
                    queue.extend(refresh)
                    unique: dict[str, AuctionCandidate] = {}
                    for item in queue:
                        unique[item.source_url] = item
                    due = sorted(unique.values(), key=_queue_priority)
                    stats.queue_due = len(due)
                    process = due[:PROCESS_LIMIT]
                    stats.queue_processed = len(process)
                    detail_sem = asyncio.Semaphore(DETAIL_CONCURRENCY)

                    async def process_one(c: AuctionCandidate):
                        async with detail_sem:
                            await self._enrich_and_analyze(client, c, stats)

                    await asyncio.gather(*(process_one(c) for c in process))
            finally:
                stats.finished_at = utcnow_naive()
                self.status.running = False
                self.status.last_run = stats
                self._update_status_metrics()
            return stats

    def get_status(self) -> IngestionStatus:
        self._update_status_metrics()
        return self.status

    def list_sources(self) -> list[AuctionSource]:
        return list(self.sources.values())

    def list_candidates(self, limit: int = 100) -> list[AuctionCandidate]:
        return sorted(self.candidates.values(), key=lambda a: a.last_seen_at, reverse=True)[:limit]

    def search(self, **kwargs):
        return repository.search_auctions(**kwargs)

    def get_auction(self, fingerprint_value: str):
        return repository.get_auction(fingerprint_value)

    def get_analysis(self, fingerprint_value: str):
        if fingerprint_value in self.analyses:
            return self.analyses[fingerprint_value]
        return repository.get_analysis(fingerprint_value)


ingestion_service = IngestionService()
