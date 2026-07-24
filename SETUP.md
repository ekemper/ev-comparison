# Setup Guide

How to get API keys and run the project.

---

## 1. Prerequisites

- **Python 3.11+**
- **Docker** (for MongoDB)
- **uv** — install with `curl -LsSf https://astral.sh/uv/install.sh | sh`

## 2. Install dependencies

```bash
uv sync
```

## 3. Start MongoDB

```bash
docker compose up -d
```

Mongo will be available at `mongodb://localhost:27017`. Data persists in a named Docker volume.

## 4. Get API keys

Copy the environment template and fill in your keys:

```bash
cp .env.example .env
```

### MarketCheck

1. Go to [marketcheck.com/pricing](https://marketcheck.com/pricing)
2. Click **Sign Up** on the Free tier (no credit card required)
3. After signup, go to your [API Dashboard](https://apidashboard.marketcheck.com/)
4. Copy your API key
5. Paste into `.env` as `MARKETCHECK_API_KEY=your_key_here`

**Free tier:** 500 calls/month, 5 req/sec, 100-mile radius

### Auto.dev

1. Go to [auto.dev/pricing](https://www.auto.dev/pricing)
2. Click **Get Started** on the Starter plan (free, no credit card)
3. After signup, go to your [Developer Dashboard](https://www.auto.dev/dashboard)
4. Copy your API key
5. Paste into `.env` as `AUTODEV_API_KEY=your_key_here`

**Free tier:** 1,000 calls/month, 5 req/sec

### Driv.ly

1. Go to [landing.driv.ly/api](https://landing.driv.ly/api)
2. Click **Get Started** on the Develop plan (free, no credit card)
3. After signup, go to your [Developer Dashboard](https://developer.driv.ly/)
4. Copy your API key / bearer token
5. Paste into `.env` as `DRIVLY_API_KEY=your_key_here`

**Free tier:** 100,000 credits/month, 2 req/sec

### Carapis (CarGurus)

1. Go to [carapis.com](https://carapis.com)
2. Sign up for the Free plan
3. After signup, go to your [Dashboard](https://carapis.com/dashboard)
4. Copy your API key
5. Paste into `.env` as `CARAPIS_API_KEY=your_key_here`

**Free tier:** 10,000 req/day (60/min), 1 parser (CarGurus only)

## 5. Run

Smoke-test all clients and run an aggregated search:

```bash
uv run python -m src.main
```

This will:
1. Test each API client individually (first page only)
2. Run a `VehicleSearch` aggregated search across all sources
3. Print a summary with counts per source and any errors
