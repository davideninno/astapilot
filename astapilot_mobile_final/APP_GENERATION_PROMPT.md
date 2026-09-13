# Master prompt — generate AstaPilot

Build a production-oriented Italian web app/PWA named **AstaPilot**: a digital consultant that automatically discovers judicial real-estate auctions, analyzes their public documents, highlights risks with evidence, calculates a transparent Asta Score, simulates the real acquisition cost and guides the user through the steps required to participate.

## Core promise

“Trova l'asta. Capisci rischi e costi. Decidi con più informazioni. Partecipa seguendo una procedura guidata.”

This is NOT a manual auction uploader and NOT a generic classifieds portal. User-facing auctions must be imported automatically by background ingestion jobs.

## Required stack

- Next.js + TypeScript + React + Tailwind for the responsive web/PWA.
- Python FastAPI service for ingestion, PDF/document processing, scoring and simulation.
- PostgreSQL + PostGIS for auctions, geo search, users, watchlists and structured extracted facts.
- Background worker/queue for source refresh and document analysis.
- S3-compatible object storage for public auction documents and generated reports.
- Pluggable AI extraction provider using strict structured JSON output. Never rely on free-form model text for deterministic calculations.

## Primary user journeys

### 1. Onboarding
Ask whether the user is looking for HOME, INVESTMENT or BOTH, then preferred areas, maximum budget, radius and property types.

### 2. Search/Home
Show automatically imported auctions. Filters: city/location/radius, province, max/min bid, property type, surface, auction date, occupancy, Asta Score, profile and document completeness. Include “Mostrami solo opportunità interessanti”.

### 3. Auction detail
Display address/map, photos, court, procedure, lot, base price, minimum bid, minimum raise, bid deadline, auction date, ownership right and document list.

The visual priority must be:
1. Procedure Gate
2. Rights Gate
3. Critical Flags
4. Confidence Score
5. Asta Score
6. Economic metrics

### 4. Analysis
Show component scores: economic, urban planning, occupancy, documentation, procedure and marketability. Every risk card must show severity C1-C4, plain-language explanation, recommended action and source document/page/excerpt when available.

C4 risks must remain visually dominant and must cap the score. Never allow a low price to visually compensate for a critical non-sanability/demolition-type risk.

### 5. Document viewer
Open the source PDF at the cited page and visually identify the supporting passage when possible.

### 6. Simulator
Inputs: bid, conservative market value, taxes, renovation, regularization, condominium costs, professional fees, other costs, contingency rate and desired margin. Outputs: total investment, gross margin, margin rate, personal bid limit and warnings.

### 7. Copilot
Contextual chat for one auction. Suggested questions: “È occupato?”, “Ci sono abusi?”, “Perché lo score è basso?”, “Qual è il rischio maggiore?”, “Quanto spenderei davvero?”, “Cosa devo verificare prima di offrire?”. Every material answer must cite the auction documents/facts and must clearly say when a fact is UNKNOWN.

### 8. Guided purchase
When the user selects “Voglio partecipare”, create a dynamic checklist derived from that sale’s documents: visit, funding, deposit, required docs, bid deadline, auction date, balance deadline and professional checks. Do not submit the auction bid or move the user’s money in this version.

### 9. Watchlist/alerts
Favorites, saved searches and alerts for new matching auctions, changed auction dates, new documents, suspension/cancellation and approaching deadlines.

### 10. Admin/operations
Separate admin-only interface for source health, coverage, failed parsers, duplicate merges, document versions, extraction conflicts, reprocessing, manual correction with audit trail and Golden Dataset review.

## Ingestion architecture

Implement a Source Registry with adapters. Include an institutional PVP adapter contract plus adapters for authorized publishers. Prefer authorized feeds/APIs when available. Public sitemap/detail parsing is only a fallback. Respect source terms/rate limits.

Every cycle must:
- refresh source directory;
- discover new auction URLs;
- refresh active existing auctions;
- parse detail pages;
- create canonical identity using court + procedure + lot;
- merge the same lot across multiple publishers;
- discover/download documents;
- SHA-256 hash documents and version changes;
- extract text, with OCR fallback for scanned PDFs;
- run deterministic extraction + schema-constrained AI extraction;
- resolve cross-document consistency;
- calculate risk factors, confidence and score;
- persist and index for search.

## Structured facts

At minimum store with confidence + provenance:
- procedure status;
- court/procedure/lot;
- ownership right;
- address/geo;
- property type/surface/rooms;
- base price/minimum bid/minimum raise;
- deposit;
- bid deadline/auction date/balance deadline;
- occupancy status;
- lease opposability/expiry;
- urban compliance/sanability;
- demolition/acquisition risk;
- cadastral inconsistencies;
- condominium arrears;
- legal disputes/constraints;
- reported physical issues;
- appraisal values and their meaning;
- document completeness.

If not explicitly supported, return UNKNOWN. Do not invent legal, urban-planning or structural conclusions.

## Risk engine

Severity:
- C1 informational
- C2 verification needed
- C3 high risk
- C4 critical

Implement score caps. Examples:
- C4 urban non-remediable: max 25
- demolition/acquisition risk: max 20
- multiple C3 risks: max 49
- single C3: max 69
- C2-only profile: max 84 unless specifically configured otherwise

Procedure statuses SUSPENDED, CANCELLED, REVOKED and ADJUDICATED block participation UX.

For HOME goal, non-full-ownership rights should trigger the Rights Gate and explain why.

## Confidence score

Keep separate from Asta Score. Base it on document coverage, extraction confidence, cross-document consistency and data freshness. Show examples such as “Score 88 / Confidence 42%: potentially interesting but insufficient evidence.” Critical risk takes precedence over low-confidence display labels.

## Design

Modern, trustworthy Italian proptech—not a court website. White/light neutral background, strong typography, compact cards, clear red/amber/green risk hierarchy, maps and mobile-first layout. Avoid gimmicky AI gradients. Make provenance and warnings easy to inspect.

## Safety/product language

Never say “compra”, “affare sicuro” or imply legal/technical certainty. Use language such as “opportunità da approfondire”, “verifica professionale necessaria”, “valore indicativo algoritmico”, “soglia personale basata sulle ipotesi inserite”. Clearly distinguish official/documented facts from algorithmic estimates and user-entered assumptions.

## Business model scaffolding

Implement feature flags/entitlements for:
- Free: search, favorites, basic auction facts, compact score.
- Single Report: one complete AI analysis/report.
- Plus: analyses, Copilot, alerts, comparisons, simulator.
- Investor: higher limits, portfolio, advanced ROI/comparables/export.
Do not hard-code pricing into core domain logic.

## Acceptance tests

The generated app is not complete unless all these pass:
1. No user must manually insert an auction to populate search.
2. Two publisher URLs for the same court/procedure/lot merge into one auction.
3. A changed source document creates a new version and triggers re-analysis.
4. “non sanabile” must not also create a “sanabile/regolarizzabile” risk.
5. A C4 demolition/non-sanability risk caps score <=25 (or stricter configured cap).
6. Suspended auction renders BLOCKED even if economics are attractive.
7. Bare ownership for HOME goal triggers Rights Gate.
8. Every critical extracted fact has provenance or is explicitly marked unsupported/UNKNOWN.
9. Search supports city/province/budget/score and excludes past auctions by default.
10. Simulation returns total investment, personal bid limit and warnings.
11. Golden Dataset regression suite protects all critical fields.
12. Admin source-health dashboard shows ingestion failures and coverage gaps.

Start by creating the database schema and API contracts, then the ingestion/analysis services, then the user UI. Seed development with synthetic/test fixtures only; do not fake national coverage or pretend a source integration exists when it does not.

## Commercial architecture — mandatory

Treat AstaPilot as a commercial SaaS from day one. Implement authentication, accounts, billing, entitlements, paywalls, usage metering, analytics and conversion instrumentation as first-class systems, not later add-ons.

### Authentication/account
Support email/password plus Google and Apple sign-in, email verification, password recovery, account deletion/export flows, user profile and onboarding preferences. Anonymous users can search and preview public auction facts; registration is required for favorites, saved searches, alerts, personalized simulation and Personal Match.

### Revenue products (configuration, not hard-coded domain logic)
Seed launch experiments with: Free €0; Analysis €14.90 one-time per auction; Complete Report €29.90 one-time; Plus €24.90/month; Investor €79.90/month; Pro €199/month. Prices must be remotely/configurably changeable and support monthly/annual variants and experiments.

### Entitlement engine
Never scatter `if plan == ...` checks. Create capability-based entitlements with quotas/reset periods and auction-scoped grants. Capabilities include SEARCH_ADVANCED, FAVORITES, SAVED_SEARCHES, BASIC_SCORE, FULL_ANALYSIS, FULL_RISK_DETAILS, DOCUMENT_PROVENANCE, SIMULATOR, PERSONAL_BID_LIMIT, COPILOT, COMPARISON, PDF_REPORT, DEAL_RADAR, PORTFOLIO, ROI_TOOLS, EXPORT, TEAM_WORKSPACE and API_ACCESS.

### Paywall rules
Public auction facts remain visible. Free users may see Asta Score summary and that critical risks exist. Never conceal the existence/severity/category of a C4 risk. Paid access unlocks full explanations, evidence/provenance, recommended actions, detailed scoring, simulator, Copilot and reports according to entitlement. No dark patterns or fake urgency.

### Billing
Integrate Stripe Checkout/Billing/Customer Portal behind a provider abstraction. Implement one-time auction purchases and subscriptions, webhook-driven state, idempotency, upgrade/downgrade, cancellation, failed-payment handling, invoices/receipts, coupons/trials and tax-ready configuration. Never trust client-side payment state.

### Cost architecture
Central auction extraction is a shared asset. A document version must be analyzed once and cached; do not rerun expensive extraction for each customer. Meter Copilot/personalized generation independently. Track per-analysis and per-user AI/data cost.

### Three scores
Keep independent: Asta Score (risk/manageability), Opportunity Score (economic attractiveness using conservative inputs) and Personal Match (fit to user goal/budget/geography/financing/risk tolerance). Never collapse them into a single opaque score.

### Retention
Implement Deal Radar (saved criteria + alerts), portfolio stages (DISCOVERED, INTERESTED, VERIFY, VISIT, OFFER, AUCTION, WON, REJECTED), auction comparison and Guided Purchase. Alert on new matches, new/changed documents, date/status changes and approaching deadlines.

### Analytics
Instrument VISITOR -> SEARCH -> DETAIL -> REGISTRATION -> ANALYSIS_PREVIEW -> PAYWALL -> CHECKOUT_STARTED -> PURCHASED -> GUIDED_PURCHASE -> RETAINED/REFERRED. Track Free-to-Paid, report-to-subscription, ARPU, MRR, churn, LTV, variable AI/data cost, gross margin and revenue per auction. Support feature flags and pricing experiments, but never experiment on safety warnings.

### Commercial admin
Add dashboard for subscriptions, one-time purchases, MRR, churn, funnel conversion, plan mix, failed payments, AI cost, gross margin, coupons, experiments and entitlement overrides with audit logs.

### Acquisition/SEO
Auction detail pages and legitimate city/province landing pages should be server-rendered/indexable when data publication rights allow. Implement canonical URLs, sitemap generation and structured metadata. Avoid thin programmatic SEO.

### Additional acceptance tests
13. Anonymous user can search/detail preview but cannot create favorites without registration.
14. A C4 risk remains visibly disclosed to Free users even when detailed analysis is paywalled.
15. One-time Analysis purchase grants FULL_ANALYSIS only for the purchased auction.
16. Subscription webhook updates entitlements idempotently and client state cannot forge access.
17. Changing a plan price does not require changing domain code.
18. Central extraction for the same document hash is reused across multiple users.
19. Usage quotas reset correctly and are enforced server-side.
20. Asta Score, Opportunity Score and Personal Match are stored/rendered independently.
21. Deal Radar can match a newly imported auction against saved criteria and enqueue an alert.
22. Every key funnel event is emitted with anonymous/user/account attribution as appropriate.
