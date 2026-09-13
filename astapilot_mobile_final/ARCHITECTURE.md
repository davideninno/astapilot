# AstaPilot — Architecture v0.9

## Product invariant

AstaPilot is not an auction listing site with an AI chat attached. The system must first establish procedural status, acquired right, document evidence and critical risks; only then may it expose economic opportunity metrics.

## Runtime pipeline

```text
Authorized/official sources
  -> source registry
  -> source-specific feed/adapters + public sitemap fallback
  -> discovery queue
  -> detail parser
  -> canonical identity (court + procedure + lot)
  -> cross-publisher dedupe/merge
  -> document discovery + content-hash versioning
  -> PDF text extraction / OCR fallback
  -> deterministic extractor
  -> schema-constrained AI extractor
  -> cross-document consistency checker
  -> Procedure Gate + Rights Gate
  -> RiskFactor engine C1-C4
  -> Confidence Score
  -> Asta Score with caps
  -> valuation/simulation
  -> user search/detail/copilot/guided purchase
```

## Non-negotiable rules

1. No manual auction insertion in the user product.
2. Manual upload exists only in admin/recovery tooling.
3. The same court/procedure/lot is one auction even if published by multiple sites.
4. Refresh active auctions repeatedly; do not treat discovery as immutable.
5. Content-hash every downloaded document and re-analyze only changed versions.
6. Every critical claim must carry document/page provenance when available.
7. `UNKNOWN` is preferable to inference for legal/technical facts.
8. C4 critical risks cap the score and remain visually dominant.
9. Procedure suspension/cancellation/revocation/adjudication blocks participation UX.
10. Economic simulation never overrides legal/technical critical flags.

## Production target stack

- Web/mobile PWA: Next.js + TypeScript + React + Tailwind.
- API/document pipeline: Python + FastAPI.
- DB: PostgreSQL + PostGIS.
- Queue: Redis-backed workers or managed cloud queue.
- Documents: S3-compatible object storage.
- Search: Postgres initially; dedicated search engine only after scale justifies it.
- AI: provider behind `StructuredExtractionProvider`; schema-constrained output only.
- Observability: structured logs, per-source health, parsing error rate, extraction confidence drift.

## Source strategy

PVP is the institutional primary reference. Publisher adapters must use authorized feeds/APIs or explicitly permitted public pages. Generic sitemap discovery remains a fallback, not the promised basis for complete national coverage. “All auctions” can only be a production promise after coverage is measured against official counts and source agreements/feed access are in place.

## Coverage KPI

Per court/province/day:

- auctions expected from official/authorized source counts;
- unique auctions indexed;
- percentage with sale notice;
- percentage with appraisal;
- percentage analyzed;
- percentage with unresolved extraction conflicts;
- median time from publication/update to AstaPilot refresh.

## AI quality gate

Maintain a human-verified Golden Dataset. Any extractor/model change must pass regression tests on critical fields before deployment. Critical fields include procedure status, acquired right, occupancy, lease opposability, urban compliance/sanability, demolition risk, minimum bid, deadline and deposit.

## Commercial platform layer v1.0

Add these bounded contexts around the auction intelligence core:

```text
Identity/Auth
  -> User/Profile/Account
  -> Entitlement Service <-> Billing Provider
  -> Usage Metering
  -> Paywall/Feature Flags

Auction Intelligence
  -> Asta Score
  -> Opportunity Score
  -> Personal Match
  -> AnalysisAccess (auction-scoped purchase/subscription)

Retention
  -> Saved Search / Deal Radar
  -> Watchlist
  -> Portfolio
  -> Alerts

Growth/Finance
  -> Analytics Events
  -> Experiments
  -> Revenue/Cost ledger
  -> Commercial Admin
```

Payment webhooks are authoritative and idempotent. Entitlements are server-side. Central document extraction is keyed by document content hash and reused across all users. Personalized Copilot usage is separately metered.
