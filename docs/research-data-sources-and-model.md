# EV Comparison: Data Sources & ML Model

APIs for collecting vehicle listing data and a recommended regression model for price interpolation/extrapolation.

---

## Tier 1 — Best APIs for This Project

These provide bulk listing data with price, mileage, year, trim, and location — exactly what the model needs.

| API | What you get | Coverage | Access | Cost |
|-----|-------------|----------|--------|------|
| **MarketCheck** | 6M+ active listings, 100+ filter params, price history, dealer + FSBO + auction | US & Canada | REST API, API key | Free tier (limited); paid from ~$200/mo |
| **Auto.dev** | Millions of active dealer listings, real-time pricing, vehicle specs | US | REST API, API key | Free tier available |
| **Driv.ly** | Aggregates KBB, Edmunds, NADA, BlackBook, MMR valuations + listing data | US | REST API, API key | Free dev tier; enterprise plans available |
| **CarGurus (via Carapis)** | Listings with deal ratings, multi-market search, EPA data | US, CA, UK | REST API | Tiered plans (100–2000 req/min) |

**Recommendation:** Start with **MarketCheck**. Largest dataset (5B+ historical listings), richest filtering (make, model, year, trim, mileage, price, ZIP), and a free tier to prototype with.

---

## Tier 2 — Valuation-Only APIs

These return a single estimated price rather than raw listings. Useful as a comparison baseline, not as training data.

| API | Data | Notes |
|-----|------|-------|
| **Manheim (MMR)** | Wholesale auction valuations, EV battery health scoring | Industry standard for wholesale. Requires dealer/partner relationship. |
| **KBB API** | Trade-in, private party, dealer retail values | Developer portal exists but access restricted to Cox Automotive partners. |
| **Edmunds TMV** | True Market Value by style, ZIP, options, color | Open API program retired. Access limited to strategic partners only. |

---

## Tier 3 — Free Supplemental APIs

| API | Data | Use case |
|-----|------|----------|
| **NHTSA vPIC** | VIN decoding, make/model/year/trim specs, safety ratings | Free, no key needed. Enrich listings with standardized vehicle specs. |
| **EPA Fuel Economy** | MPG / MPGe / range for EVs by year/make/model | Free CSV + API. Critical feature for EV valuation (range affects price). |

---

## Standard Dimensions for the Model

Features to collect per listing, ranked by typical importance in car price prediction.

| Feature | Type | Source | Why it matters |
|---------|------|--------|----------------|
| Year / Age | Numeric | Listing | Primary depreciation driver |
| Mileage (odometer) | Numeric | Listing | Strongest single predictor of used car value |
| Trim / package | Categorical | Listing + VIN decode | Separates base from premium (e.g. SR vs Long Range) |
| Condition | Ordinal | Listing | New / CPO / Used / Fair / Salvage |
| Drivetrain | Categorical | Listing + VIN | AWD vs RWD (e.g. Model 3 RWD vs AWD) |
| Battery capacity / range | Numeric | EPA + listing | EV-specific: range anxiety premium |
| Location (ZIP / region) | Categorical | Listing | Regional price variation (CA vs TX vs Midwest) |
| Color (exterior) | Categorical | Listing | Moderate effect (white/black neutral; unusual colors +/-) |
| Seller type | Categorical | Listing | Dealer vs private party vs auction |
| Days on market | Numeric | MarketCheck | Proxy for demand; stale listings = overpriced |

---

## Recommended ML Model: XGBoost Regression

Gradient-boosted trees consistently outperform linear regression, random forest, and neural nets on tabular car pricing data. Published benchmarks achieve R² of 0.91–0.94.

**Why XGBoost:**
- Handles mixed feature types (numeric + categorical)
- Built-in feature importance
- Robust to outliers
- Fast training

**Alternatives to benchmark against:** Linear Regression (baseline), Random Forest, LightGBM. Train all three and compare RMSE / MAE / R² on the test set.

---

## Python Pipeline

### 1. Data collection

```python
import requests
import pandas as pd

API_KEY = "your_marketcheck_key"
BASE = "https://mc-api.marketcheck.com/v2/search/car/active"

def fetch_listings(make: str, model: str, year_min: int, year_max: int):
    """Pull all listings for a make/model across a year range."""
    all_rows = []
    for year in range(year_min, year_max + 1):
        params = {
            "api_key": API_KEY,
            "make": make,
            "model": model,
            "year": str(year),
            "rows": 50,
            "start": 0,
        }
        resp = requests.get(BASE, params=params)
        listings = resp.json().get("listings", [])
        for l in listings:
            all_rows.append({
                "year": l.get("build", {}).get("year"),
                "trim": l.get("build", {}).get("trim"),
                "mileage": l.get("miles"),
                "price": l.get("price"),
                "drivetrain": l.get("build", {}).get("drivetrain"),
                "exterior_color": l.get("exterior_color"),
                "seller_type": l.get("seller_type"),
                "city": l.get("dealer", {}).get("city"),
                "state": l.get("dealer", {}).get("state"),
                "days_on_market": l.get("dom"),
            })
    return pd.DataFrame(all_rows)
```

### 2. Preprocessing and feature engineering

```python
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import numpy as np

def preprocess(df: pd.DataFrame) -> tuple:
    df = df.dropna(subset=["price", "mileage", "year"])
    df = df[(df["price"] > 5_000) & (df["price"] < 150_000)]

    df["age"] = 2026 - df["year"]
    df["mileage_per_year"] = df["mileage"] / df["age"].clip(lower=1)
    df["log_mileage"] = np.log1p(df["mileage"])

    cat_cols = ["trim", "drivetrain", "exterior_color",
                "seller_type", "state"]
    encoders = {}
    for col in cat_cols:
        df[col] = df[col].fillna("unknown")
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le

    features = ["age", "mileage", "log_mileage", "mileage_per_year",
                "days_on_market"] + cat_cols
    X = df[features]
    y = df["price"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    return X_train, X_test, y_train, y_test, encoders, features
```

### 3. Model training and evaluation

```python
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

model = XGBRegressor(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
)
model.fit(X_train, y_train,
          eval_set=[(X_test, y_test)],
          verbose=50)

preds = model.predict(X_test)
print(f"MAE:  ${mean_absolute_error(y_test, preds):,.0f}")
print(f"RMSE: ${np.sqrt(mean_squared_error(y_test, preds)):,.0f}")
print(f"R²:   {r2_score(y_test, preds):.3f}")
```

### 4. Interpolation / extrapolation

```python
def estimate_value(model, encoders, features,
                    year, mileage, trim, drivetrain,
                    color="unknown", seller="dealer",
                    state="CA", dom=30):
    """Predict price for a vehicle not in the dataset."""
    age = 2026 - year
    row = {
        "age": age,
        "mileage": mileage,
        "log_mileage": np.log1p(mileage),
        "mileage_per_year": mileage / max(age, 1),
        "days_on_market": dom,
        "trim": encoders["trim"].transform([trim])[0],
        "drivetrain": encoders["drivetrain"].transform([drivetrain])[0],
        "exterior_color": encoders["exterior_color"].transform([color])[0],
        "seller_type": encoders["seller_type"].transform([seller])[0],
        "state": encoders["state"].transform([state])[0],
    }
    X = pd.DataFrame([row])[features]
    return model.predict(X)[0]

# Example: 2023 Model Y Long Range, 25k miles, AWD, Colorado
price = estimate_value(
    model, encoders, features,
    year=2023, mileage=25_000,
    trim="Long Range", drivetrain="AWD",
    state="CO"
)
print(f"Estimated value: ${price:,.0f}")
```

---

## Dependencies

```
pandas>=2.2
numpy>=1.26
scikit-learn>=1.5
xgboost>=2.1
requests>=2.32
matplotlib>=3.9
```

---

## Extrapolation Caveat

Tree-based models cannot extrapolate beyond the range of training data. If you query a year/mileage combination outside the training distribution (e.g., a 2027 model year or 300k miles when max training data is 200k), the prediction clamps to the nearest leaf. For out-of-range scenarios, consider adding a linear correction term or using a blended linear + XGBoost approach.

---

*Research compiled May 2026. API availability and pricing may change.*
