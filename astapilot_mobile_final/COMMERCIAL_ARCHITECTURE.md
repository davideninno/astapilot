# AstaPilot — Commercial Architecture v1.0

## Objective
AstaPilot is a revenue-generating vertical SaaS/marketplace for Italian judicial real-estate auctions. The commercial system must monetize proprietary analysis and workflow while keeping public auction facts accessible and never hiding the existence of a critical C4 risk behind a paywall.

## Revenue model
1. Free acquisition layer.
2. Pay-per-auction Analysis (€14.90 launch test).
3. Complete Report (€29.90 launch test).
4. Plus subscription (€24.90/month launch test).
5. Investor subscription (€79.90/month launch test).
6. Pro workspace (€199/month launch test; configurable).
7. Later: professional referrals/marketplace, B2B intelligence/API.

All prices are configuration/experiments, never domain constants.

## Funnel
VISITOR -> SEARCH -> AUCTION DETAIL -> REGISTRATION -> ANALYSIS PREVIEW -> PAYWALL -> CHECKOUT -> PAID ANALYSIS -> GUIDED PURCHASE -> RETENTION/REFERRAL.

Require registration for favorites, saved searches, alerts, simulations and personalized match. Allow anonymous search/detail preview for SEO and acquisition.

## Entitlements
Use capabilities, not plan-name conditionals:
SEARCH_ADVANCED, FAVORITES, SAVED_SEARCHES, BASIC_SCORE, FULL_ANALYSIS, FULL_RISK_DETAILS, DOCUMENT_PROVENANCE, SIMULATOR, PERSONAL_BID_LIMIT, COPILOT, COMPARISON, PDF_REPORT, DEAL_RADAR, PORTFOLIO, ROI_TOOLS, EXPORT, TEAM_WORKSPACE, API_ACCESS.

Each entitlement supports quotas and reset periods. Purchases may grant auction-scoped entitlements.

## Monetization guardrails
- Never hide that a C4 risk exists. Free may see category/severity; paid unlocks detailed evidence, impact, actions and report.
- Never manufacture urgency or risk.
- Show billing terms clearly and make cancellation self-service.
- Cache central auction intelligence: analyze a document version once, sell access many times. Do not rerun expensive extraction per customer.
- Meter personalized AI separately from central extraction.

## Scores
Keep three independent concepts:
- Asta Score: procedural/documentary/technical risk profile.
- Opportunity Score: economic attractiveness under conservative assumptions.
- Personal Match: fit to the user's goal, budget, geography, financing and risk tolerance.

Do not collapse these into one number.

## Retention products
- Deal Radar: saved criteria + alerts for newly discovered matching auctions and material changes.
- Portfolio pipeline: Discovered, Interested, Verify, Visit, Offer, Auction, Won, Rejected.
- Comparison: side-by-side auctions with risk, economics and match.
- Guided Purchase: dynamic checklist and deadlines.

## Billing
Production target: Stripe Checkout + Billing + Customer Portal + webhooks. Support one-time products and subscriptions, upgrades/downgrades, coupons/trials, failed-payment recovery, invoices/receipts and tax configuration. Webhooks are source of truth for payment state; handlers must be idempotent.

## Commercial data model
User, Account, UserProfile, Plan, Price, Subscription, Entitlement, EntitlementGrant, UsageCounter, Purchase, PaymentEvent, SavedSearch, AlertRule, WatchlistItem, PortfolioItem, AnalysisAccess, Referral, ExperimentAssignment, AnalyticsEvent.

## Unit economics
Track per user/account and cohort:
CAC, activation, registration conversion, paywall view, checkout start, checkout conversion, report attach rate, Free->Paid, Report->Subscription, ARPU, MRR, ARR, churn, LTV, AI/document cost, gross margin, payback period, revenue per auction, Deal Radar retention.

## Launch economics targets
These are operating targets, not forecasts:
- Central extraction reused across customers.
- Gross margin target >= 75% on software revenue after AI/data variable cost.
- Instrument every paid feature before launch.
- No paid acquisition scaling until a measured cohort shows acceptable conversion and retention.

## SEO/acquisition
Create indexable auction pages and high-quality city/province landing pages only for data legitimately publishable. Add structured metadata, canonical URLs and sitemap generation. Avoid thin programmatic SEO pages.

## Experiments
Feature-flag pricing and packaging. Initial tests: €14.90 analysis vs €19.90; report upsell; Plus monthly vs annual; number of free previews; registration timing. Never A/B test safety warnings or conceal critical risks.

## Admin commercial dashboard
MRR, active paid users, one-time revenue, churn, conversion funnel, plan mix, AI cost, gross margin, failed payments, coupon usage, top acquisition pages, high-converting auction profiles and entitlement overrides with audit log.
