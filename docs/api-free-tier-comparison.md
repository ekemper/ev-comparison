# API Free Tier Comparison

How much car listing data can you reliably pull from each Tier 1 source for free?

---

## At a Glance

| | MarketCheck | Auto.dev | Driv.ly | Carapis (CarGurus) |
|---|---|---|---|---|
| **Free calls/month** | 500 | 1,000 | 100,000 credits | ~3,000/mo (100/day) |
| **Rate limit** | 5 req/sec | 5 req/sec | 2 req/sec | 1 req/sec (60/min) |
| **Results per page** | up to 50 | up to 100 | ~100 (default) | up to 100 |
| **Max pagination depth** | 500 rows | Unlimited | Unlimited | Unlimited |
| **Realistic listings/month** | ~10,000–25,000 | ~100,000 | ~10,000,000 | ~150,000–300,000 |
| **Signup** | Email, no CC | Email, no CC | Email, no CC | Email, free plan |
| **Key restriction** | 100-mile radius | None documented | 2 req/sec throttle | 1 parser only |

---

## MarketCheck

**Portal:** https://marketcheck.com/pricing

### What you get free
- 500 API calls per month
- 5 requests per second
- Access to every endpoint (inventory search, VIN lookup, price history, dealer, etc.)
- No credit card required

### What's restricted on free
- **100-mile radius cap** — searches are geofenced. You must vary the ZIP code across calls to cover the country.
- **500-row pagination limit** — any single query can return at most 500 rows total, regardless of how many exist. Paid tiers allow 1,500+.
- Default page size ~50 rows, so paginating one query to its 500-row cap costs ~10 API calls.

### Realistic free data yield
With 500 calls/month and ~10 calls per paginated query, you can run ~50 unique searches. Each returns up to 500 listings.

**Best case:** 50 queries x 500 rows = **25,000 listings/month**
**Practical estimate:** ~10,000–15,000 unique listings (overlap between queries, not all queries hit 500 results)

### Verdict
The 500-call cap is tight. Enough to build and test a pipeline for one or two make/model combinations. Not enough to do a broad national sweep. The 100-mile radius forces you to issue separate queries per region, burning calls fast.

---

## Auto.dev

**Portal:** https://www.auto.dev/pricing

### What you get free
- 1,000 API calls per month (Starter plan)
- 5 requests per second
- Access to Vehicle Listings, VIN Decode, and Vehicle Photos
- No credit card required

### What's restricted on free
- After 1,000 calls, each additional Listings call costs $0.002 (pay-as-you-go)
- No documented pagination depth limit
- Page size up to 100 results per call

### Realistic free data yield
With 1,000 calls at 100 listings per page:

**Best case:** 1,000 x 100 = **100,000 listings/month**
**Practical estimate:** ~50,000–80,000 unique listings (some calls will be VIN lookups, filters that return fewer results, etc.)

### Verdict
Best ratio of free calls to data volume. The 100-per-page pagination means each call is efficient. The pay-as-you-go overflow ($0.002/call = $2 per 1,000 extra calls) is cheap if you need a bit more. Strong choice for the primary data source on a free budget.

---

## Driv.ly

**Portal:** https://landing.driv.ly/api

### What you get free
- 100,000 API credits per month (Develop plan)
- 2 requests per second
- No credit card required
- Additional credits at $0.50 per 1,000 if you go over

### What's restricted on free
- **2 req/sec rate limit** — the lowest of all four. At sustained max throughput: 2 x 60 x 60 = 7,200 requests/hour.
- No guaranteed SLA
- Credit-per-request mapping is not publicly documented (assumed 1 credit = 1 request based on pricing tiers)

### Realistic free data yield
Assuming 1 credit per request and ~100 listings per page:

**Best case:** 100,000 x 100 = **10,000,000 listings/month**
**Rate-limited reality:** At 2 req/sec sustained, you'd exhaust 100k credits in ~14 hours of continuous pulling. That's still ~10M listings in theory.

**Practical estimate:** You won't need anywhere near 10M listings. The free tier is effectively unlimited for this project's scale.

### But read the fine print
- Driv.ly's credit system may charge >1 credit for some endpoints (valuations, enriched data). The docs don't break this down.
- The listings data quality can be inconsistent — Driv.ly aggregates from many sources, and some fields may be sparse.
- The 2 req/sec cap means bulk pulls are slow. Budget ~6 hours to pull 40,000 listings.

### Verdict
By raw volume, the most generous free tier by far. The 100k credits/month is overkill for training data collection. Main risk is data quality and undocumented credit costs for certain endpoints.

---

## Carapis (CarGurus)

**Portal:** https://carapis.com

### What you get free
- **Rate limits:** 60 req/min, 1,000 req/hour, 10,000 req/day
- 1 parser (CarGurus only — other markets like Auto.ru, Mobile.de require paid plans)
- Email support (48-hour response)

### Conflicting information
The FAQ mentions "first 100 requests are free" as an onboarding statement, but the rate limits documentation consistently shows 10,000 req/day on the free tier. The safe assumption is that the free tier allows 10,000 req/day, but it's possible the "free" tier requires signup and the first 100 are available without an account.

### What's restricted on free
- **1 parser only** — you get CarGurus data but can't access their other 25+ market parsers
- Page size 50 default, 100 max
- No guaranteed uptime SLA

### Realistic free data yield
At 10,000 req/day x 100 listings/page x 30 days:

**Best case:** 10,000 x 100 x 30 = **30,000,000 listings/month**
**Conservative (100 req/day reading):** 100 x 100 x 30 = **300,000 listings/month**

**Practical estimate at 10k/day:** ~150,000–300,000 unique CarGurus listings/month (heavy deduplication expected since CarGurus inventory refreshes, not replaces, daily)

### Verdict
If the 10k/day limit holds, this is very generous. CarGurus data includes deal ratings (great deal / good deal / fair deal) which is unique among the four sources. Worth confirming the actual free-tier daily limit by signing up and checking the dashboard.

---

## Free Supplemental APIs (Unlimited)

These two government APIs have no API keys and no meaningful rate limits:

| API | Data | Limits | How to use |
|-----|------|--------|------------|
| **NHTSA vPIC** | VIN decode → year, make, model, trim, body, engine, drivetrain | No key needed. Automated rate control (undisclosed threshold). Bulk alternative: download the full database (~2GB SQL dump). | Enrich every listing with standardized specs. |
| **EPA Fuel Economy** | MPG/MPGe/range for every vehicle 1984–present | No key needed. No documented limits. Full dataset available as a single CSV download (~15MB). | Download the CSV once. Join on year+make+model to get EV range and efficiency. No API calls needed. |

**Recommendation:** Download the EPA CSV and the NHTSA SQL dump. Use them as local lookup tables. Zero API cost, zero rate limit concerns.

---

## Strategy: Maximizing Free Data

### For building and testing the pipeline
Use **Auto.dev** as the primary source. 1,000 free calls at 100 listings/page gives you up to 100k listings — more than enough to build, test, and debug every client.

### For collecting training data at scale
Use **Driv.ly** for bulk pulls (100k credits/month) supplemented by **Carapis** for CarGurus deal ratings. Together they can yield hundreds of thousands of deduplicated listings per month.

### For data quality validation
Use **MarketCheck** (smaller free tier, but highest data quality — 100+ filter params, price history, days-on-market). Run targeted queries for your specific make/model to validate that the Driv.ly and Carapis data maps correctly.

### Monthly budget: $0

| Source | Calls | Listings (est.) | Role |
|--------|-------|-----------------|------|
| Auto.dev | 1,000 | 50,000–80,000 | Primary development & testing |
| Driv.ly | 100,000 credits | 100,000+ | Bulk training data |
| Carapis | 3,000–300,000 | 50,000–150,000 | CarGurus deal ratings |
| MarketCheck | 500 | 10,000–15,000 | Quality validation, price history |
| NHTSA | Unlimited | Full VIN database | Spec enrichment |
| EPA | N/A (CSV) | All vehicles | Range/MPG enrichment |
| **Total** | — | **200,000–400,000+** | — |

This is more than sufficient to train an XGBoost model. Typical car pricing models achieve good R² with 10,000–50,000 listings for a single make/model.
