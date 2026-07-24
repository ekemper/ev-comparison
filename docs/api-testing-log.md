# API Testing Log

What we tried, what worked, and what didn't — June 2026.

---

## Auto.dev — Working

### Setup

- Signed up at https://www.auto.dev/pricing (free Starter plan)
- Key stored in `.env` as `AUTODEV_API_KEY`
- Made all API keys optional in `src/config.py` so the app can run with any subset of keys

### API changes from original plan

- The client code was written targeting `https://api.auto.dev/listings`, but the actual working URL is `https://auto.dev/api/listings`
- Free tier caps results at **20 per page** regardless of the `limit` parameter (we requested 100, got 20)
- To get a total count, append `includes=total` to the query — the response then includes a `total` field
- Pagination info comes in a `links` object with `self`, `first`, `prev`, `next`, `toggleFacets`, `toggleTotal`
- Response wraps listings in a `data` array (not `records`)

### Validation calls (4 API calls used)

**Call 1** — Shape validation (`limit=5`, Denver 200mi):
- Status: 200
- Response keys: `links`, `data`
- Confirmed field mapping: `vehicle.make`, `vehicle.model`, `vehicle.year`, `retailListing.price`, `retailListing.miles` all present
- Bonus fields not in original docs: `vehicle.exteriorColor`, `vehicle.interiorColor`, `vehicle.bodyStyle`, `history.accidentCount`, `vehicle.baseInvoice`, `vehicle.baseMsrp`

**Call 2** — Pagination structure (same params):
- `links` object provides `toggleTotal` and `toggleFacets` URLs
- No `total` field unless `includes=total` is passed

**Calls 3-4** — Total counts:
- Denver 200mi radius: **64 listings**
- National (no zip/distance): **765 listings**

### Full data pull (39 API calls)

- Pulled all 765 Nissan Leaf listings nationally
- 20 results per page × 39 pages (38 full + 1 partial with 5)
- 765 unique VINs (zero duplicates)
- Saved to `data/nissan_leaf_raw.json` (1.3 MB)
- 0.25s delay between calls

### Dataset summary

| Metric | Value |
|--------|-------|
| Total listings | 765 |
| Years covered | 2011–2025 (every model year) |
| Price range | $800 – $39,004 |
| Price median | $13,499 |
| Price mean | $13,616 |
| Mileage range | 1 – 138,101 mi |
| Mileage median | 37,136 mi |
| Trims | S (234), SV (231), SV Plus (169), SL (88), SL Plus (25), S Plus (18) |
| Conditions | Used (697), CPO (50), New (18) |
| States | 40 states — top: CA (125), WA (75), CO (65), FL (41), TX (39) |
| Price coverage | 100% (765/765 have price) |
| Mileage coverage | 99% (760/765 have mileage) |

### API budget

| Purpose | Calls |
|---------|-------|
| Validation (shape + totals) | 4 |
| Full national pull | 39 |
| **Total used** | **43** |
| **Remaining (of 1,000/month)** | **957** |

---

## Carapis (CarGurus) — Not Working (404)

### Setup

- Signed up at https://carapis.com (free plan)
- Key stored in `.env` as `CARAPIS_API_KEY`
- Key format: `car_` prefix, 47 characters total

### What the docs say

The Carapis docs (https://carapis.com/api/getting-started, updated June 5, 2026) specify:

- Base URL: `https://api.carapis.com/v2`
- Endpoint: `GET /v2/listings`
- Auth: `Authorization: Bearer <API_KEY>` header
- Required param: `source` (platform slug, e.g. `cargurus`)
- Response: `{ count, page, limit, results: [...] }`

CarGurus is listed as a supported platform at https://carapis.com/platforms/north-america/cargurus with the slug `cargurus`.

### What we tried

**All returned HTTP 404** — the path does not exist on the server.

| # | Method | URL | Auth | Result |
|---|--------|-----|------|--------|
| 1 | POST | `https://api.carapis.com/v1/parsers/cargurus/search` | Bearer | 404 |
| 2 | GET | `https://api.carapis.com/v1/parsers/cargurus/search` | Bearer | 404 |
| 3 | GET | `https://api.carapis.com/v1/cargurus/search` | Bearer | 404 |
| 4 | POST | `https://api.carapis.com/v1/cargurus/search` | Bearer | 404 |
| 5 | GET | `https://api.carapis.com/cargurus/search` | Bearer | 404 |
| 6 | GET | `https://api.carapis.com/v1/listings` | Bearer | 404 |
| 7 | POST | `https://api.carapis.com/parsers/cargurus/search` | Bearer | 404 |
| 8 | GET | `https://api.carapis.com/parsers/cargurus/search` | Bearer | 404 |
| 9 | GET | `https://api.carapis.com/v2/listings?source=cargurus` | Bearer | 404 |
| 10 | GET | `https://api.carapis.com/v2/listings?source=cargurus` | x-api-key | 404 |
| 11 | GET | `https://api.carapis.com/v2/listings?source=cargurus&api_key=` | query param | 404 |
| 12 | GET | `https://api.carapis.com/v2/listings` (no source) | Bearer | 404 |

### Diagnosis

- The 404 comes from their server (confirmed via `curl -I`), not from Cloudflare blocking
- The HTTP response includes `server: cloudflare` headers and Django-style error markup, confirming the request reaches their infrastructure but the route doesn't match
- This is **not** an authentication issue — a 401 or 403 would indicate auth problems. A 404 means the endpoint path doesn't exist.

### Likely causes

1. The free-tier account may need a manual activation step before the API routes are enabled
2. The documented API may only be available on paid plans, despite the free plan being advertised
3. The API may be in maintenance or have been moved to a different subdomain

### Recommendation

- Check the Carapis dashboard (https://carapis.com/dashboard or https://my.carapis.com) for an "activate API" step
- Contact Carapis support to confirm the free plan includes API access
- The `src/clients/carapis.py` client code needs updating to use `/v2/listings` with the `source` param once the API is accessible

---

## Code changes made during testing

1. **`src/config.py`** — Changed all four API keys from `_require()` to `_optional()` so the app runs with any subset of keys
2. **`src/main.py`** — Added `--source` flag to test a single source, `--skip-db` flag to skip MongoDB, and auto-detection of which API keys are configured
3. **`scripts/pull_nissan_leaf.py`** — Script that pulled the full Nissan Leaf dataset (saves to `data/nissan_leaf_raw.json`)
4. **`scripts/test_autodev*.py`** — Validation scripts for Auto.dev (can be deleted)
5. **`scripts/test_carapis*.py`** — Validation scripts for Carapis (can be deleted)

---

## Services not yet tested

| Service | Key added | Status |
|---------|-----------|--------|
| MarketCheck | No | Not attempted — sign up at https://marketcheck.com/pricing |
| Driv.ly | No | Not attempted — sign up at https://landing.driv.ly/api |
