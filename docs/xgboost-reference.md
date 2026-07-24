# XGBoost: A Mathematically Rigorous Reference

A practitioner's guide to Extreme Gradient Boosting — from the math to the Python tooling.

---

## Table of Contents

1. [What XGBoost Is (and Isn't)](#1-what-xgboost-is-and-isnt)
2. [The Math: Objective Function](#2-the-math-objective-function)
3. [The Math: Taylor Expansion Trick](#3-the-math-taylor-expansion-trick)
4. [The Math: Optimal Leaf Weights and Split Gain](#4-the-math-optimal-leaf-weights-and-split-gain)
5. [Regularization](#5-regularization)
6. [Tree Construction Algorithms](#6-tree-construction-algorithms)
7. [Handling Missing Values](#7-handling-missing-values)
8. [Shrinkage and Stochastic Sampling](#8-shrinkage-and-stochastic-sampling)
9. [Loss Functions for Regression](#9-loss-functions-for-regression)
10. [Hyperparameters: What They Mean and How to Tune Them](#10-hyperparameters)
11. [Evaluation Metrics](#11-evaluation-metrics)
12. [Cross-Validation and Early Stopping](#12-cross-validation-and-early-stopping)
13. [Feature Importance and Interpretation](#13-feature-importance-and-interpretation)
14. [Python Tooling Reference](#14-python-tooling-reference)
15. [XGBoost vs. Other Methods](#15-xgboost-vs-other-methods)
16. [Common Pitfalls](#16-common-pitfalls)

---

## 1. What XGBoost Is (and Isn't)

XGBoost (Extreme Gradient Boosting) is a **regularized gradient boosting** framework that builds an ensemble of decision trees sequentially, where each new tree corrects the errors of the previous ensemble.

It is **not** a novel algorithm in the theoretical sense. It is an engineered, optimized implementation of gradient tree boosting (Friedman, 2001) with two key additions:

1. **Explicit regularization** of tree complexity (leaf weights and tree size)
2. **Second-order Taylor expansion** of the loss function, giving it Newton-method convergence properties instead of simple gradient descent

These two additions, combined with systems-level optimizations (parallelized split finding, cache-aware access, out-of-core computation), make it dominant on tabular data.

**Reference:** Chen & Guestrin, "XGBoost: A Scalable Tree Boosting System" (KDD 2016)

---

## 2. The Math: Objective Function

### The ensemble model

Given a dataset with n examples, the prediction for example i after T boosting rounds is an additive sum of T trees:

\[
\hat{y}_i = \sum_{t=1}^{T} f_t(x_i), \quad f_t \in \mathcal{F}
\]

where \(\mathcal{F}\) is the space of regression trees (CART). Each tree \(f_t\) maps an input vector to a scalar leaf weight.

### The objective

XGBoost minimizes a **regularized** objective:

\[
\mathcal{L}(\phi) = \underbrace{\sum_{i=1}^{n} l(\hat{y}_i, y_i)}_{\text{training loss}} + \underbrace{\sum_{t=1}^{T} \Omega(f_t)}_{\text{regularization}}
\]

where:
- \(l\) is any differentiable convex loss function (e.g., squared error, logistic)
- \(\Omega(f)\) penalizes tree complexity

### The regularization term

\[
\Omega(f) = \gamma T + \frac{1}{2}\lambda \sum_{j=1}^{T} w_j^2
\]

- \(T\) = number of leaves in the tree
- \(w_j\) = weight (prediction value) of leaf j
- \(\gamma\) = penalty per additional leaf (controls tree size)
- \(\lambda\) = L2 penalty on leaf weights (controls weight magnitude)

An optional L1 term \(\alpha |w_j|\) can also be added.

---

## 3. The Math: Taylor Expansion Trick

### The additive training setup

At round t, we have the prediction from the previous t-1 trees, and we're adding a new tree \(f_t\):

\[
\hat{y}_i^{(t)} = \hat{y}_i^{(t-1)} + f_t(x_i)
\]

The objective at round t is:

\[
\mathcal{L}^{(t)} = \sum_{i=1}^{n} l\Big(y_i,\; \hat{y}_i^{(t-1)} + f_t(x_i)\Big) + \Omega(f_t) + \text{const}
\]

### The second-order approximation

Apply a second-order Taylor expansion around \(\hat{y}_i^{(t-1)}\):

\[
l\Big(y_i,\; \hat{y}_i^{(t-1)} + f_t(x_i)\Big) \approx l\Big(y_i,\; \hat{y}_i^{(t-1)}\Big) + g_i \cdot f_t(x_i) + \frac{1}{2} h_i \cdot f_t^2(x_i)
\]

where:

\[
g_i = \frac{\partial\, l(y_i,\; \hat{y}_i^{(t-1)})}{\partial\, \hat{y}_i^{(t-1)}} \qquad \text{(gradient: first derivative)}
\]

\[
h_i = \frac{\partial^2 l(y_i,\; \hat{y}_i^{(t-1)})}{\partial\, (\hat{y}_i^{(t-1)})^2} \qquad \text{(hessian: second derivative)}
\]

### Why this matters

- Standard gradient boosting (Friedman) only uses \(g_i\) — it does gradient descent in function space.
- XGBoost uses both \(g_i\) and \(h_i\) — it does **Newton's method** in function space.
- Newton's method converges faster because it accounts for the curvature of the loss surface, not just its slope.

Dropping the constant term \(l(y_i, \hat{y}_i^{(t-1)})\), the simplified objective is:

\[
\tilde{\mathcal{L}}^{(t)} = \sum_{i=1}^{n} \Big[ g_i \cdot f_t(x_i) + \frac{1}{2} h_i \cdot f_t^2(x_i) \Big] + \Omega(f_t)
\]

This is a **quadratic function of the leaf weights** — it can be solved exactly.

---

## 4. The Math: Optimal Leaf Weights and Split Gain

### Regrouping by leaf

Define \(I_j = \{i \mid q(x_i) = j\}\) as the set of examples assigned to leaf j by the tree structure q. Since all examples in the same leaf get the same weight \(w_j\):

\[
\tilde{\mathcal{L}}^{(t)} = \sum_{j=1}^{T} \bigg[ \Big(\sum_{i \in I_j} g_i\Big) w_j + \frac{1}{2}\Big(\sum_{i \in I_j} h_i + \lambda\Big) w_j^2 \bigg] + \gamma T
\]

Define shorthand:

\[
G_j = \sum_{i \in I_j} g_i, \qquad H_j = \sum_{i \in I_j} h_i
\]

### Optimal leaf weight

Taking the derivative with respect to \(w_j\) and setting to zero:

\[
w_j^* = -\frac{G_j}{H_j + \lambda}
\]

This is the closed-form optimal prediction value for leaf j. Note how \(\lambda\) shrinks the weight toward zero — this is the L2 regularization acting directly on the prediction.

### Optimal objective value

Substituting \(w_j^*\) back:

\[
\tilde{\mathcal{L}}^* = -\frac{1}{2} \sum_{j=1}^{T} \frac{G_j^2}{H_j + \lambda} + \gamma T
\]

This is the **quality score** of a tree structure. Lower is better.

### Split gain formula

When evaluating a split that divides leaf j into left (L) and right (R) children:

\[
\text{Gain} = \frac{1}{2} \left[ \frac{G_L^2}{H_L + \lambda} + \frac{G_R^2}{H_R + \lambda} - \frac{(G_L + G_R)^2}{H_L + H_R + \lambda} \right] - \gamma
\]

Interpretation of each term:
- \(\frac{G_L^2}{H_L + \lambda}\) — score of the left child
- \(\frac{G_R^2}{H_R + \lambda}\) — score of the right child
- \(\frac{(G_L+G_R)^2}{H_L+H_R+\lambda}\) — score if we don't split (keep as one leaf)
- \(-\gamma\) — penalty for adding one more leaf

A split is made only if \(\text{Gain} > 0\). The \(\gamma\) term acts as a built-in **pruning** mechanism: a split must improve the objective by at least \(\gamma\) to be worth the added complexity.

---

## 5. Regularization

XGBoost has three regularization mechanisms that work together:

| Mechanism | Parameter | Effect |
|-----------|-----------|--------|
| L2 on leaf weights | `reg_lambda` (\(\lambda\)) | Shrinks leaf predictions toward zero. Appears in the denominator of \(w_j^*\). Default: 1. |
| L1 on leaf weights | `reg_alpha` (\(\alpha\)) | Drives small leaf weights exactly to zero (sparsity). Default: 0. |
| Leaf count penalty | `gamma` (\(\gamma\)) | Minimum gain required to make a split. Acts as pre-pruning. Default: 0. |
| Min child weight | `min_child_weight` | Minimum sum of \(h_i\) in a child node. Prevents splits on tiny subsets. Default: 1. |

**Key insight:** Unlike post-hoc pruning in standard CART, XGBoost's \(\gamma\) provides **mathematically principled pruning** integrated into the objective function.

---

## 6. Tree Construction Algorithms

XGBoost supports three split-finding strategies:

### Exact greedy (`tree_method="exact"`)

Enumerates all possible splits on all features. For each feature:
1. Sort examples by feature value
2. Scan left to right, accumulating \(G_L, H_L\)
3. Compute gain for each split point
4. Pick the split with maximum gain

Complexity: \(O(n \cdot d \cdot n \log n)\) where d = number of features. Exact but expensive for large datasets.

### Approximate (`tree_method="approx"`)

Uses a **weighted quantile sketch** to propose candidate split points:
1. For each feature, compute percentile boundaries using the hessian values \(h_i\) as weights
2. Only evaluate gain at these candidate points
3. Rebuild candidates before each tree

The hessian weighting ensures more split candidates in regions where the model is uncertain (high curvature).

### Histogram-based (`tree_method="hist"`)

The default and fastest method:
1. Discretize features into integer-valued bins (histograms) before training
2. Build gradient histograms per bin during tree construction
3. Uses the "subtraction trick": \(\text{hist}(\text{sibling}) = \text{hist}(\text{parent}) - \text{hist}(\text{child})\)

Complexity: \(O(n \cdot d)\) per level. This is what makes XGBoost fast on large datasets.

---

## 7. Handling Missing Values

XGBoost has a **sparsity-aware split finding** algorithm:

For each split, it tries routing all instances with missing values to both the left and right child, and picks whichever direction maximizes the gain. This "default direction" is learned from data, not set by the user.

This means:
- You do **not** need to impute missing values before training
- The model learns the optimal treatment of missing data at every split
- This also handles implicit sparsity (e.g., one-hot encoded categoricals)

---

## 8. Shrinkage and Stochastic Sampling

### Shrinkage (learning rate)

After computing each tree, its contribution is scaled by \(\eta\) (learning rate):

\[
\hat{y}_i^{(t)} = \hat{y}_i^{(t-1)} + \eta \cdot f_t(x_i)
\]

Lower \(\eta\) means each tree has less influence, requiring more trees but reducing overfitting. Think of it as "taking smaller steps."

### Stochastic sampling

At each boosting round, XGBoost can randomly sample:
- **Rows** (`subsample`): fraction of training examples used per tree
- **Columns per tree** (`colsample_bytree`): fraction of features per tree
- **Columns per level** (`colsample_bylevel`): fraction of features per tree depth level
- **Columns per split** (`colsample_bynode`): fraction of features per split

These are multiplicative. If `colsample_bytree=0.8` and `colsample_bylevel=0.8`, each level sees \(0.8 \times 0.8 = 64\%\) of features.

This is analogous to the bagging in Random Forests and serves the same purpose: decorrelating trees and reducing variance.

---

## 9. Loss Functions for Regression

For our car pricing use case (continuous target), the relevant loss functions are:

### Squared error (default: `objective="reg:squarederror"`)

\[
l(y_i, \hat{y}_i) = \frac{1}{2}(y_i - \hat{y}_i)^2
\]

Gradients:
\[
g_i = \hat{y}_i - y_i, \qquad h_i = 1
\]

The hessian is constant (= 1), so all examples have equal "weight" in determining splits. This is the simplest and most common choice.

### Squared log error (`objective="reg:squaredlogerror"`)

\[
l(y_i, \hat{y}_i) = \frac{1}{2}\big[\log(\hat{y}_i + 1) - \log(y_i + 1)\big]^2
\]

Useful when you care about relative (percentage) errors rather than absolute errors. Good for price prediction where a $1000 error on a $10k car matters more than on a $100k car.

### Absolute error / Huber loss (`objective="reg:absoluteerror"`)

\[
l(y_i, \hat{y}_i) = |y_i - \hat{y}_i|
\]

More robust to outliers than squared error. XGBoost uses a smooth approximation internally because pure MAE has zero hessian (which breaks the leaf weight formula).

### Quantile regression (`objective="reg:quantileerror"`)

Predicts a specific quantile (e.g., median, 10th percentile, 90th percentile) rather than the mean. Set `quantile_alpha` to the desired quantile (0.5 for median).

Useful for building **prediction intervals**: train three models at quantiles 0.1, 0.5, and 0.9 to get a range estimate.

### Custom objectives

You can define any loss by providing gradient and hessian functions:

```python
def custom_obj(y_pred, dtrain):
    y_true = dtrain.get_label()
    grad = ...  # ∂l/∂ŷ for each example
    hess = ...  # ∂²l/∂ŷ² for each example
    return grad, hess

model = xgb.train({"disable_default_eval_metric": True},
                   dtrain, obj=custom_obj)
```

**Important:** The hessian must be positive (or at least non-negative) for the optimization to be well-defined. If your loss has regions where \(h_i = 0\), add a small constant (e.g., \(h_i = \max(h_i, \epsilon)\)).

---

## 10. Hyperparameters

### Tier 1: Tune these first

| Parameter | Default | Range | What it controls |
|-----------|---------|-------|-----------------|
| `n_estimators` | 100 | 50–5000 | Number of boosting rounds. More rounds = more complex model. |
| `learning_rate` (`eta`) | 0.3 | 0.01–0.3 | Shrinkage per round. Lower values need more rounds but generalize better. |
| `max_depth` | 6 | 2–10 | Maximum tree depth. Controls interaction order. Depth d captures d-way feature interactions. |
| `min_child_weight` | 1 | 1–100 | Minimum sum of hessian in a child. Higher = more conservative splits. For squared error (hessian=1), this equals minimum number of examples per leaf. |

### Tier 2: Tune for overfitting control

| Parameter | Default | Range | What it controls |
|-----------|---------|-------|-----------------|
| `subsample` | 1.0 | 0.5–1.0 | Row sampling per tree. |
| `colsample_bytree` | 1.0 | 0.3–1.0 | Feature sampling per tree. |
| `gamma` | 0 | 0–5 | Minimum split gain (\(\gamma\) in the gain formula). |
| `reg_lambda` | 1 | 0–10 | L2 regularization (\(\lambda\)). |
| `reg_alpha` | 0 | 0–5 | L1 regularization (\(\alpha\)). |

### Tier 3: Rarely tune

| Parameter | Default | Notes |
|-----------|---------|-------|
| `tree_method` | `"auto"` | Usually picks `"hist"`. Only change for specific needs. |
| `max_leaves` | 0 (unlimited) | Alternative to `max_depth` for leaf-wise growth. |
| `scale_pos_weight` | 1 | For imbalanced classification. Not relevant for regression. |
| `max_bin` | 256 | Number of histogram bins. Increase for higher precision, decrease for speed. |

### Recommended tuning procedure

```python
from sklearn.model_selection import GridSearchCV
from xgboost import XGBRegressor

# Step 1: Fix learning_rate=0.1, find n_estimators with early stopping
model = XGBRegressor(learning_rate=0.1, n_estimators=1000,
                     early_stopping_rounds=50)
model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
best_n = model.best_iteration
# best_n tells you how many rounds to use

# Step 2: Tune max_depth and min_child_weight
param_grid_1 = {
    "max_depth": [3, 4, 5, 6, 7, 8],
    "min_child_weight": [1, 3, 5, 10],
}
gs1 = GridSearchCV(
    XGBRegressor(learning_rate=0.1, n_estimators=best_n),
    param_grid_1, scoring="neg_root_mean_squared_error", cv=5
)
gs1.fit(X_train, y_train)

# Step 3: Tune subsample and colsample_bytree
param_grid_2 = {
    "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
    "colsample_bytree": [0.6, 0.7, 0.8, 0.9, 1.0],
}
gs2 = GridSearchCV(
    XGBRegressor(learning_rate=0.1, n_estimators=best_n,
                 **gs1.best_params_),
    param_grid_2, scoring="neg_root_mean_squared_error", cv=5
)
gs2.fit(X_train, y_train)

# Step 4: Tune regularization
param_grid_3 = {
    "reg_lambda": [0, 0.1, 1, 5, 10],
    "reg_alpha": [0, 0.01, 0.1, 1],
    "gamma": [0, 0.1, 0.5, 1],
}
gs3 = GridSearchCV(
    XGBRegressor(learning_rate=0.1, n_estimators=best_n,
                 **gs1.best_params_, **gs2.best_params_),
    param_grid_3, scoring="neg_root_mean_squared_error", cv=5
)
gs3.fit(X_train, y_train)

# Step 5: Lower learning_rate, increase n_estimators, retrain with early stopping
final_model = XGBRegressor(
    learning_rate=0.01,
    n_estimators=5000,
    early_stopping_rounds=100,
    **gs1.best_params_,
    **gs2.best_params_,
    **gs3.best_params_,
)
final_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
```

---

## 11. Evaluation Metrics

### Regression metrics

| Metric | Formula | Interpretation | When to use |
|--------|---------|----------------|-------------|
| **MAE** | \(\frac{1}{n}\sum|y_i - \hat{y}_i|\) | Average absolute dollar error | Easy to interpret. "On average, predictions are off by $X." Robust to outliers. |
| **RMSE** | \(\sqrt{\frac{1}{n}\sum(y_i - \hat{y}_i)^2}\) | Root mean squared dollar error | Penalizes large errors more. Same units as target. Standard in competitions. |
| **R²** | \(1 - \frac{\sum(y_i-\hat{y}_i)^2}{\sum(y_i-\bar{y})^2}\) | Fraction of variance explained | 1.0 = perfect, 0.0 = predicts the mean, <0 = worse than mean. Good for comparing models. |
| **MAPE** | \(\frac{100}{n}\sum\left|\frac{y_i-\hat{y}_i}{y_i}\right|\) | Average percentage error | Interpretable as "off by X%". Problematic when \(y_i\) is near zero. |
| **MedAE** | \(\text{median}(|y_i - \hat{y}_i|)\) | Median absolute error | Robust to outliers. "Half the predictions are within $X." |

### For car pricing specifically

Use **RMSE** as the primary metric (penalizes big misses on expensive cars), **MAE** as a secondary sanity check, and **R²** for comparing across datasets. Report all three.

### sklearn implementation

```python
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    median_absolute_error,
    mean_absolute_percentage_error,
)
import numpy as np

preds = model.predict(X_test)

mae   = mean_absolute_error(y_test, preds)
rmse  = np.sqrt(mean_squared_error(y_test, preds))
r2    = r2_score(y_test, preds)
medae = median_absolute_error(y_test, preds)
mape  = mean_absolute_percentage_error(y_test, preds) * 100

print(f"MAE:   ${mae:,.0f}")
print(f"RMSE:  ${rmse:,.0f}")
print(f"R²:    {r2:.4f}")
print(f"MedAE: ${medae:,.0f}")
print(f"MAPE:  {mape:.1f}%")
```

---

## 12. Cross-Validation and Early Stopping

### Why cross-validation

A single train/test split is noisy. Cross-validation (CV) gives you:
- A more reliable estimate of generalization performance
- Confidence intervals on that estimate
- Protection against unlucky splits

### Using sklearn cross-validation

```python
from sklearn.model_selection import cross_val_score

model = XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=6)

scores = cross_val_score(
    model, X, y,
    cv=5,
    scoring="neg_root_mean_squared_error",
)

print(f"RMSE: {-scores.mean():,.0f} ± {scores.std():,.0f}")
```

### Using XGBoost's native `xgb.cv()`

More control than sklearn, including built-in early stopping:

```python
import xgboost as xgb

dtrain = xgb.DMatrix(X_train, label=y_train)

params = {
    "objective": "reg:squarederror",
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 1,
}

cv_results = xgb.cv(
    params,
    dtrain,
    num_boost_round=2000,
    nfold=5,
    metrics=["rmse", "mae"],
    early_stopping_rounds=50,
    verbose_eval=100,
    seed=42,
)

best_round = cv_results.shape[0]
best_rmse = cv_results["test-rmse-mean"].iloc[-1]
print(f"Best round: {best_round}, CV RMSE: {best_rmse:,.0f}")
```

### Early stopping

Stops training when the validation metric hasn't improved for N rounds:

```python
model = XGBRegressor(
    n_estimators=5000,       # set high
    learning_rate=0.01,
    early_stopping_rounds=50,
)
model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    verbose=False,
)

print(f"Stopped at round {model.best_iteration}")
print(f"Best validation RMSE: {model.best_score:.0f}")
```

**Important:** Early stopping requires a held-out validation set passed via `eval_set`. The model trains on `X_train` and monitors performance on `X_val`. The final model uses `best_iteration` trees, not all `n_estimators`.

---

## 13. Feature Importance and Interpretation

### Method 1: Built-in importance (fast, approximate)

```python
import matplotlib.pyplot as plt

# sklearn API — uses "gain" by default
importances = model.feature_importances_
sorted_idx = importances.argsort()

plt.barh(range(len(sorted_idx)), importances[sorted_idx])
plt.yticks(range(len(sorted_idx)), X.columns[sorted_idx])
plt.xlabel("Feature Importance (Gain)")
plt.tight_layout()
plt.show()
```

Importance types (via the native API):

```python
booster = model.get_booster()
# "weight" — number of times used as a split feature
# "gain"   — average gain when used as a split feature
# "cover"  — average number of examples affected
# "total_gain" — cumulative gain
# "total_cover" — cumulative cover
importance = booster.get_score(importance_type="gain")
```

**Limitation:** Built-in importance can be biased toward high-cardinality features. A feature with many unique values gets more split opportunities, inflating its importance.

### Method 2: Permutation importance (reliable, model-agnostic)

Randomly shuffle one feature at a time and measure how much the model's performance degrades:

```python
from sklearn.inspection import permutation_importance

result = permutation_importance(
    model, X_test, y_test,
    n_repeats=10,
    scoring="neg_root_mean_squared_error",
    random_state=42,
)

sorted_idx = result.importances_mean.argsort()
plt.boxplot(result.importances[sorted_idx].T, vert=False,
            labels=X.columns[sorted_idx])
plt.xlabel("Decrease in RMSE")
plt.tight_layout()
plt.show()
```

**Advantage:** Measured on held-out data, not training data. Reflects actual predictive contribution. Includes uncertainty (via repeats).

### Method 3: SHAP values (gold standard, expensive)

SHAP (SHapley Additive exPlanations) provides per-prediction feature attributions based on game theory:

```python
import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# Global feature importance (bar plot)
shap.summary_plot(shap_values, X_test, plot_type="bar")

# Detailed feature effects (beeswarm plot)
shap.summary_plot(shap_values, X_test)

# Single prediction explanation
shap.force_plot(explainer.expected_value, shap_values[0], X_test.iloc[0])

# Dependence plot: how one feature affects predictions
shap.dependence_plot("mileage", shap_values, X_test)
```

**What SHAP tells you that others don't:**
- Not just "mileage is important" but "high mileage pushes the prediction down by $X"
- Direction and magnitude of each feature's effect
- Feature interactions (via interaction values)
- Why a specific prediction was made (local explanations)

---

## 14. Python Tooling Reference

### Libraries

| Library | Install | Purpose |
|---------|---------|---------|
| `xgboost` | `pip install xgboost` | The model itself |
| `scikit-learn` | `pip install scikit-learn` | Preprocessing, metrics, cross-validation, GridSearchCV |
| `shap` | `pip install shap` | Model interpretation |
| `matplotlib` | `pip install matplotlib` | Plotting |
| `optuna` | `pip install optuna` | Bayesian hyperparameter optimization (alternative to GridSearchCV) |

### Two APIs: Native vs. Sklearn

XGBoost offers two Python APIs:

**Native API** — more control, required for `xgb.cv()`:

```python
import xgboost as xgb

dtrain = xgb.DMatrix(X_train, label=y_train)
dtest = xgb.DMatrix(X_test, label=y_test)

params = {
    "objective": "reg:squarederror",
    "max_depth": 6,
    "learning_rate": 0.05,
    "eval_metric": "rmse",
}

model = xgb.train(
    params, dtrain,
    num_boost_round=500,
    evals=[(dtest, "test")],
    early_stopping_rounds=50,
    verbose_eval=100,
)
preds = model.predict(dtest)
```

**Sklearn API** — drop-in compatible with sklearn pipelines:

```python
from xgboost import XGBRegressor

model = XGBRegressor(
    objective="reg:squarederror",
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    early_stopping_rounds=50,
)
model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
preds = model.predict(X_test)
```

**Recommendation:** Use the sklearn API for most work (cleaner interface, works with GridSearchCV, pipelines, etc.). Switch to native API only when you need `xgb.cv()` or custom callbacks.

### Saving and loading models

```python
# Save
model.save_model("model.json")          # JSON format (readable)
model.save_model("model.ubj")           # UBJSON format (smaller, faster)

# Load
loaded = xgb.XGBRegressor()
loaded.load_model("model.json")
preds = loaded.predict(X_new)
```

### Optuna for Bayesian hyperparameter search

More efficient than GridSearchCV for large parameter spaces:

```python
import optuna

def objective(trial):
    params = {
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.3, 1.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.01, 10, log=True),
        "reg_alpha": trial.suggest_float("reg_alpha", 0.001, 1, log=True),
        "gamma": trial.suggest_float("gamma", 0, 5),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 20),
    }
    model = XGBRegressor(n_estimators=1000, early_stopping_rounds=50, **params)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    preds = model.predict(X_val)
    return np.sqrt(mean_squared_error(y_val, preds))

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=100)

print(f"Best RMSE: {study.best_value:,.0f}")
print(f"Best params: {study.best_params}")
```

---

## 15. XGBoost vs. Other Methods

| | XGBoost | LightGBM | Random Forest | Linear Regression |
|---|---|---|---|---|
| **Training** | Sequential (boosting) | Sequential (boosting) | Parallel (bagging) | Single pass |
| **Tree growth** | Level-wise (default) | Leaf-wise | Level-wise | N/A |
| **Speed** | Fast | Faster (especially on large data) | Fast | Fastest |
| **Accuracy on tabular data** | Excellent | Excellent | Good | Baseline |
| **Regularization** | L1, L2, gamma, min_child_weight | L1, L2, min_data_in_leaf | Max features, max depth | L1 (Lasso), L2 (Ridge) |
| **Missing values** | Built-in (learns direction) | Built-in | Requires imputation | Requires imputation |
| **Overfitting risk** | Medium (with regularization) | Medium-high (leaf-wise can overfit) | Low (bagging is inherently regularizing) | Low (but underfits) |
| **Interpretability** | SHAP, importance | SHAP, importance | Importance | Coefficients |
| **When to choose** | Default for tabular ML | Very large datasets, speed-critical | Quick baseline, stable results | Interpretability, linearity check |

**For car pricing:** XGBoost and LightGBM will both outperform linear regression and random forest. Train both and compare. The difference is usually small (<1% R²), but XGBoost tends to be more stable with default settings.

---

## 16. Common Pitfalls

### Data leakage
- Don't include `price` from other sources as a feature when predicting price
- Don't use `days_on_market` if it's correlated with the price drop (it's a consequence, not a cause)
- Split data **before** any preprocessing that uses target information

### Overfitting to small datasets
- With <1000 examples, tree models can memorize the training set
- Use aggressive regularization: lower max_depth (3-4), higher lambda (5-10), lower learning_rate (0.01)
- Always monitor train vs. validation loss curves

### Target encoding categorical features
- `LabelEncoder` assigns arbitrary integers — the model may learn spurious ordinal relationships
- For high-cardinality categoricals (e.g., `trim` with 50+ values), consider `TargetEncoder` from sklearn or `OrdinalEncoder` with careful ordering
- XGBoost >= 2.0 has native categorical support: set `enable_categorical=True` and pass categoricals as `pd.Categorical`

### Log-transforming the target
- Car prices are right-skewed (most cars $20-40k, some >$100k)
- Training on `log(price)` instead of `price` often improves RMSE because it reduces the influence of expensive outliers
- Remember to `np.exp()` predictions back to dollar values for evaluation

```python
import numpy as np

y_train_log = np.log1p(y_train)  # log(1 + y) handles y=0
model.fit(X_train, y_train_log)

preds_log = model.predict(X_test)
preds = np.expm1(preds_log)      # inverse: exp(x) - 1
```

### Extrapolation
- Tree models **cannot extrapolate** beyond the range of training data
- If training data has prices $5k-$100k, the model physically cannot predict $120k — it returns the value of the nearest leaf
- For out-of-range predictions, consider a blended model (XGBoost + linear correction) or ensure your training data covers the full range

---

*References:*
- *Chen & Guestrin, "XGBoost: A Scalable Tree Boosting System" (KDD 2016)*
- *Friedman, "Greedy Function Approximation: A Gradient Boosting Machine" (2001)*
- *XGBoost documentation: https://xgboost.readthedocs.io/*
- *SHAP documentation: https://shap.readthedocs.io/*
