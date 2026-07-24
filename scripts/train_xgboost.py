"""
XGBoost price prediction model for Nissan Leaf listings.

Loads raw JSON data, engineers features, trains an XGBoost regressor
with early stopping, and reports evaluation metrics + feature importance.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

CURRENT_YEAR = 2026
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "nissan_leaf_raw.json"
MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
PLOTS_DIR = Path(__file__).resolve().parent.parent / "plots"

TRIM_RANK = {"S": 1, "S PLUS": 2, "SV": 3, "SV PLUS": 4, "SL": 5, "SL PLUS": 6}


# ── Data loading & feature engineering ────────────────────────────────────────


def load_raw_listings(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return data["listings"]


def build_dataframe(listings: list[dict]) -> pd.DataFrame:
    """Flatten nested JSON into a feature-ready DataFrame."""
    rows = []
    for entry in listings:
        vehicle = entry.get("vehicle", {})
        retail = entry.get("retailListing") or {}
        history = entry.get("history") or {}

        price = retail.get("price")
        miles = retail.get("miles")
        if not price or price <= 0 or not miles:
            continue

        row = {
            "year": vehicle.get("year"),
            "trim": vehicle.get("trim"),
            "base_msrp": vehicle.get("baseMsrp", 0),
            "drivetrain": vehicle.get("drivetrain"),
            "exterior_color": vehicle.get("exteriorColor"),
            "mileage": miles,
            "price": price,
            "state": retail.get("state"),
            "cpo": int(retail.get("cpo", False)),
            "used": int(retail.get("used", True)),
            "photo_count": retail.get("photoCount", 0),
            "accident_count": history.get("accidentCount", 0),
            "owner_count": history.get("ownerCount", 0),
            "one_owner": int(history.get("oneOwner", False)),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create derived features and encode categoricals."""
    df = df.copy()

    df["vehicle_age"] = CURRENT_YEAR - df["year"]
    df["mileage_per_year"] = df["mileage"] / df["vehicle_age"].clip(lower=1)
    df["depreciation_ratio"] = df["price"] / df["base_msrp"].clip(lower=1)

    df["trim_rank"] = df["trim"].map(TRIM_RANK).fillna(0).astype(int)

    color_counts = df["exterior_color"].value_counts()
    common_colors = set(color_counts[color_counts >= 15].index)
    df["color_group"] = df["exterior_color"].apply(
        lambda c: c if c in common_colors else "Other"
    )
    df["color_encoded"] = pd.Categorical(df["color_group"]).codes

    state_counts = df["state"].value_counts()
    top_states = set(state_counts[state_counts >= 20].index)
    df["state_group"] = df["state"].apply(
        lambda s: s if s in top_states else "Other"
    )
    df["state_encoded"] = pd.Categorical(df["state_group"]).codes

    df["is_plus_trim"] = df["trim"].str.contains("PLUS", na=False).astype(int)
    df["mileage_log"] = np.log1p(df["mileage"])

    return df


FEATURE_COLS = [
    "year",
    "vehicle_age",
    "mileage",
    "mileage_log",
    "mileage_per_year",
    "base_msrp",
    "trim_rank",
    "is_plus_trim",
    "cpo",
    "used",
    "photo_count",
    "accident_count",
    "owner_count",
    "one_owner",
    "color_encoded",
    "state_encoded",
]

TARGET_COL = "price"


# ── Training ──────────────────────────────────────────────────────────────────


def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> XGBRegressor:
    model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=2000,
        learning_rate=0.05,
        max_depth=4,
        min_child_weight=10,
        subsample=0.8,
        colsample_bytree=0.7,
        reg_lambda=5.0,
        reg_alpha=0.5,
        gamma=1.0,
        early_stopping_rounds=50,
        random_state=42,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_train, y_train), (X_val, y_val)],
        verbose=50,
    )

    return model


# ── Evaluation ────────────────────────────────────────────────────────────────


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, label: str) -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    medae = median_absolute_error(y_true, y_pred)
    mape = mean_absolute_percentage_error(y_true, y_pred) * 100

    print(f"\n{'─' * 50}")
    print(f"  {label}")
    print(f"{'─' * 50}")
    print(f"  MAE:   ${mae:>10,.0f}")
    print(f"  RMSE:  ${rmse:>10,.0f}")
    print(f"  MedAE: ${medae:>10,.0f}")
    print(f"  R²:     {r2:>10.4f}")
    print(f"  MAPE:   {mape:>10.1f}%")
    print(f"{'─' * 50}")

    return {"mae": mae, "rmse": rmse, "r2": r2, "medae": medae, "mape": mape}


# ── Plots ─────────────────────────────────────────────────────────────────────


def plot_feature_importance(model: XGBRegressor, feature_names: list[str], out_dir: Path):
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(range(len(sorted_idx)), importances[sorted_idx], color="#2196F3")
    ax.set_yticks(range(len(sorted_idx)))
    ax.set_yticklabels([feature_names[i] for i in sorted_idx])
    ax.set_xlabel("Feature Importance (Gain)")
    ax.set_title("XGBoost Feature Importance — Nissan Leaf Pricing")
    fig.tight_layout()
    fig.savefig(out_dir / "feature_importance.png", dpi=150)
    plt.close(fig)
    print(f"\n  Saved: {out_dir / 'feature_importance.png'}")


def plot_predictions_vs_actual(y_true, y_pred, label: str, out_dir: Path):
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(y_true, y_pred, alpha=0.4, s=20, color="#4CAF50")
    lo = min(y_true.min(), y_pred.min()) * 0.9
    hi = max(y_true.max(), y_pred.max()) * 1.1
    ax.plot([lo, hi], [lo, hi], "r--", lw=1.5, label="Perfect prediction")
    ax.set_xlabel("Actual Price ($)")
    ax.set_ylabel("Predicted Price ($)")
    ax.set_title(f"Predicted vs Actual — {label}")
    ax.legend()
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    fig.tight_layout()
    fname = f"pred_vs_actual_{label.lower().replace(' ', '_')}.png"
    fig.savefig(out_dir / fname, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_dir / fname}")


def plot_residuals(y_true, y_pred, label: str, out_dir: Path):
    residuals = y_pred - y_true

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    axes[0].scatter(y_pred, residuals, alpha=0.4, s=20, color="#FF9800")
    axes[0].axhline(0, color="red", linestyle="--", lw=1.5)
    axes[0].set_xlabel("Predicted Price ($)")
    axes[0].set_ylabel("Residual ($)")
    axes[0].set_title(f"Residuals vs Predicted — {label}")

    axes[1].hist(residuals, bins=40, color="#9C27B0", edgecolor="white", alpha=0.8)
    axes[1].axvline(0, color="red", linestyle="--", lw=1.5)
    axes[1].set_xlabel("Residual ($)")
    axes[1].set_ylabel("Count")
    axes[1].set_title(f"Residual Distribution — {label}")

    fig.tight_layout()
    fname = f"residuals_{label.lower().replace(' ', '_')}.png"
    fig.savefig(out_dir / fname, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_dir / fname}")


def plot_learning_curves(model: XGBRegressor, out_dir: Path):
    results = model.evals_result()
    train_rmse = results["validation_0"]["rmse"]
    val_rmse = results["validation_1"]["rmse"]
    epochs = range(len(train_rmse))

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(epochs, train_rmse, label="Train RMSE", color="#2196F3", lw=1.5)
    ax.plot(epochs, val_rmse, label="Validation RMSE", color="#F44336", lw=1.5)
    ax.set_xlabel("Boosting Round")
    ax.set_ylabel("RMSE ($)")
    ax.set_title("Learning Curves")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "learning_curves.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_dir / 'learning_curves.png'}")


def plot_price_by_age(df: pd.DataFrame, model: XGBRegressor, feature_cols: list[str], out_dir: Path):
    """Show model's learned depreciation curve vs actual data."""
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.scatter(df["vehicle_age"], df["price"], alpha=0.3, s=15, color="#78909C", label="Actual")

    ages = np.arange(0, df["vehicle_age"].max() + 1)
    median_row = df[feature_cols].median()
    synthetic = pd.DataFrame([median_row] * len(ages), columns=feature_cols)
    synthetic["vehicle_age"] = ages
    synthetic["year"] = CURRENT_YEAR - ages
    preds = model.predict(synthetic)
    ax.plot(ages, preds, color="#F44336", lw=2.5, label="Model (median features)")

    ax.set_xlabel("Vehicle Age (years)")
    ax.set_ylabel("Price ($)")
    ax.set_title("Price vs Vehicle Age — Model Depreciation Curve")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "depreciation_curve.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_dir / 'depreciation_curve.png'}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("  XGBoost Price Model — Nissan Leaf")
    print("=" * 60)

    MODEL_DIR.mkdir(exist_ok=True)
    PLOTS_DIR.mkdir(exist_ok=True)

    # Load & prepare data
    raw = load_raw_listings(DATA_PATH)
    print(f"\n  Raw listings loaded: {len(raw)}")

    df = build_dataframe(raw)
    print(f"  After filtering (price>0, has mileage): {len(df)}")

    df = engineer_features(df)

    # Drop the depreciation_ratio from features — it leaks the target
    feature_cols = [c for c in FEATURE_COLS if c in df.columns]
    X = df[feature_cols]
    y = df[TARGET_COL]

    print(f"  Features: {len(feature_cols)}")
    print(f"  Target: {TARGET_COL}")
    print(f"  Price stats: mean=${y.mean():,.0f}  median=${y.median():,.0f}  "
          f"std=${y.std():,.0f}")

    # Train / Validation split — 80/20, stratified by year to keep
    # year distribution balanced across both sets
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=df["year"],
    )
    print(f"\n  Train size: {len(X_train)}")
    print(f"  Val size:   {len(X_val)}")

    # Train
    print("\n  Training XGBoost...")
    model = train_model(X_train, y_train, X_val, y_val)
    best_round = model.best_iteration
    best_score = model.best_score
    print(f"\n  Best iteration: {best_round} (val RMSE: ${best_score:,.0f})")
    print(f"  Early stopped: trained {best_round} of {model.n_estimators} max rounds")

    # Evaluate — uses best_iteration automatically when early stopping is on
    train_preds = model.predict(X_train)
    val_preds = model.predict(X_val)

    train_metrics = evaluate(y_train.values, train_preds, "Training Set")
    val_metrics = evaluate(y_val.values, val_preds, "Validation Set")

    # Feature importance (tabular)
    print("\n  Feature Importance (Gain):")
    importances = dict(zip(feature_cols, model.feature_importances_))
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        bar = "█" * int(imp * 100)
        print(f"    {feat:<20s}  {imp:.4f}  {bar}")

    # Validation set: worst predictions
    val_df = df.iloc[X_val.index].copy()
    val_df["predicted"] = val_preds
    val_df["error"] = val_df["predicted"] - val_df["price"]
    val_df["abs_error"] = val_df["error"].abs()
    val_df["pct_error"] = (val_df["abs_error"] / val_df["price"]) * 100

    print("\n  Worst 10 predictions (validation):")
    worst = val_df.nlargest(10, "abs_error")
    for _, r in worst.iterrows():
        print(
            f"    {int(r['year'])} {r['trim']:<10s}  "
            f"{int(r['mileage']):>7,} mi  "
            f"actual=${r['price']:>8,.0f}  "
            f"pred=${r['predicted']:>8,.0f}  "
            f"err=${r['error']:>+8,.0f}  "
            f"({r['pct_error']:.0f}%)"
        )

    # Plots
    print("\n  Generating plots...")
    plot_feature_importance(model, feature_cols, PLOTS_DIR)
    plot_predictions_vs_actual(y_val.values, val_preds, "Validation", PLOTS_DIR)
    plot_predictions_vs_actual(y_train.values, train_preds, "Training", PLOTS_DIR)
    plot_residuals(y_val.values, val_preds, "Validation", PLOTS_DIR)
    plot_learning_curves(model, PLOTS_DIR)
    plot_price_by_age(df, model, feature_cols, PLOTS_DIR)

    # Save model
    model_path = MODEL_DIR / "nissan_leaf_xgb.json"
    model.save_model(str(model_path))
    print(f"\n  Model saved: {model_path}")

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    gap = val_metrics["rmse"] - train_metrics["rmse"]
    print(f"  Train RMSE:  ${train_metrics['rmse']:>8,.0f}   R²: {train_metrics['r2']:.4f}")
    print(f"  Val RMSE:    ${val_metrics['rmse']:>8,.0f}   R²: {val_metrics['r2']:.4f}")
    print(f"  Gap:         ${gap:>8,.0f}   (overfitting indicator)")
    if gap > 1000:
        print("  ⚠ Noticeable train/val gap — consider more regularization")
    else:
        print("  ✓ Train/val gap looks healthy")
    print("=" * 60)


if __name__ == "__main__":
    main()
