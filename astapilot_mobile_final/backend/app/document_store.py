from __future__ import annotations
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path

import httpx

from .ingestion_models import AuctionCandidate, PipelineStatus
from .time_utils import utcnow_naive

STORAGE_ROOT = Path(os.getenv("ASTAPILOT_STORAGE", "/mnt/data/astapilot_storage"))
MAX_DOCUMENT_BYTES = int(os.getenv("MAX_DOCUMENT_BYTES", str(40 * 1024 * 1024)))


def _safe_name(url: str, document_type: str, digest: str) -> str:
    tail = url.split("?")[0].rstrip("/").split("/")[-1] or "document"
    tail = re.sub(r"[^A-Za-z0-9._-]+", "_", tail)[:100]
    return f"{document_type.lower()}_{digest[:12]}_{tail}"


async def download_documents(client: httpx.AsyncClient, auction: AuctionCandidate) -> tuple[int, int]:
    """Download public documents with content hashing.

    Returns (downloaded_or_changed, unchanged). Content-addressing prevents needless
    reprocessing when a publisher keeps the same file URL across refresh cycles.
    """
    if not auction.fingerprint:
        return 0, 0
    folder = STORAGE_ROOT / auction.fingerprint[:2] / auction.fingerprint
    folder.mkdir(parents=True, exist_ok=True)
    changed = 0
    unchanged = 0
    for doc in auction.documents:
        try:
            r = await client.get(doc.url, follow_redirects=True)
            if r.status_code != 200:
                continue
            body = r.content
            if not body or len(body) > MAX_DOCUMENT_BYTES:
                continue
            digest = hashlib.sha256(body).hexdigest()
            if doc.sha256 == digest and doc.local_path and Path(doc.local_path).exists():
                unchanged += 1
                continue
            name = _safe_name(doc.url, doc.document_type, digest)
            path = folder / name
            path.write_bytes(body)
            if doc.sha256 and doc.sha256 != digest:
                doc.version += 1
            doc.sha256 = digest
            doc.bytes = len(body)
            doc.local_path = str(path)
            doc.content_type = r.headers.get("content-type")
            doc.downloaded_at = utcnow_naive()
            changed += 1
        except Exception:
            continue
    if changed or unchanged or not auction.documents:
        auction.pipeline_status = PipelineStatus.DOCUMENTS_DOWNLOADED
    return changed, unchanged
