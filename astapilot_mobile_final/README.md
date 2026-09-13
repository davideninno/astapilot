# AstaPilot v0.9 — App-ready Core

AstaPilot is a zero-input auction intelligence prototype. User-facing auctions are automatically discovered/imported; the system deduplicates cross-publisher listings, versions documents, extracts risks with provenance, calculates Asta Score/Confidence and exposes search + simulation APIs.

## What changed since v0.3

- cross-publisher canonical identity based on court + procedure + lot;
- persistent source registry;
- refresh of existing active auctions instead of ingest-once behavior;
- SHA-256 document versioning and re-analysis path;
- safer risk extraction with ordered regex rules and non-sanable/sanable conflict prevention;
- expanded risk catalog;
- critical risks take precedence over low-confidence labels;
- indexed search API by city/province/type/budget/score/profile/date;
- auction detail API combining facts + analysis;
- economic simulator and personal bid limit;
- explicit schema contract for future JSON-constrained AI extraction;
- app-ready UI prototype;
- architecture and master generation prompt.

## Current automated pipeline

```text
Ministry authorized-source registry + configured source adapters
 -> source discovery
 -> detail fetch
 -> canonical identity / cross-site merge
 -> document discovery
 -> content-hash download/versioning
 -> PDF text extraction
 -> deterministic structured risk extraction
 -> Procedure/Rights gates
 -> RiskFactor C1-C4
 -> Confidence + Asta Score caps
 -> persistence/search/API/UI
```

## Important coverage statement

The architecture is designed for national automatic coverage, but the prototype must NOT claim “all Italian auctions” until official/authorized feed/API integrations and measured coverage justify that claim. The PVP adapter is deliberately a contract point rather than an invented undocumented endpoint. Generic public sitemap discovery is a fallback only.

## Run

```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open `frontend/index.html`.

Useful environment variables:

```bash
AUTO_INGESTION_ENABLED=true
INGESTION_INTERVAL_SECONDS=21600
INGESTION_PROCESS_LIMIT=60
AUCTION_REFRESH_HOURS=12
SOURCE_CONCURRENCY=6
DETAIL_CONCURRENCY=4
ASTAPILOT_STORAGE=/mnt/data/astapilot_storage
ASTAPILOT_DB=/mnt/data/astapilot_data.sqlite3
MAX_DOCUMENT_BYTES=41943040
```

## API

- `GET /health`
- `GET /sources`
- `GET /ingestion/status`
- `GET /auctions?city=&province=&max_bid=&score_min=`
- `GET /auctions/{fingerprint}`
- `GET /auctions/{fingerprint}/analysis`
- `POST /simulation`
- `POST /analyze` (engine testing/backoffice)
- `POST /admin/ingestion/run` (admin/debug only)

## Test suite

```bash
cd backend
python -m pytest -q
```

Current regression suite: 16 tests, including critical scoring, ten risk scenarios, zero-input analysis, cross-publisher identity, non-sanable negation and simulation/search behavior.

## Next implementation step

Use `APP_GENERATION_PROMPT.md` to generate the production application around this domain model. The first production integration milestone is real authorized source/feed coverage; the first AI milestone is schema-constrained extraction against a human-verified Golden Dataset.

## v1.0 commercial decisions
The app-ready specification now treats AstaPilot as a commercial SaaS: anonymous acquisition, registration funnel, configurable Free/one-time/subscription products, capability entitlements, Stripe-ready billing, usage metering, Asta/Opportunity/Personal Match separation, Deal Radar, portfolio, conversion analytics, unit-economics instrumentation and commercial admin. See `COMMERCIAL_ARCHITECTURE.md` and the mandatory commercial section in `APP_GENERATION_PROMPT.md`.
