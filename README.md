# Pharmaceutical Chargeback Prediction Dashboard

An interactive analytics dashboard for forecasting pharmaceutical **chargebacks (CB)** —
the rebates a manufacturer owes wholesalers when they sell contracted customers below
list price. Built for Piramal Critical Care during a consulting engagement.

Two complementary forecasting approaches behind one dark-themed UI:

- **Excel Accrual Model** — replicates the finance team's *CB Forecast Model* accrual
  logic, recomputed in-app from raw Gross Sales + CB Detail uploads:
  `Accrual = Sales Qty × Est CB% × Avg CB Per Unit`.
- **ML Model (V7)** — a 5-layer stacked-generalization model predicting CB at the
  Agreement × SKU (contract × product) level, aggregated to product and portfolio.

> **No client data is included in this repository.** All chargeback, sales, and
> customer files are confidential and excluded via `.gitignore`. The code, model
> architecture, and aggregate results are shown; the underlying records are not.

---

## The ML model — V7 stacked generalization

V7 predicts monthly chargeback dollars per contract×product pair, layering several
techniques to stay accurate across very different pair behaviours (from $100K/month
flagship products to long-tail volatile pairs):

1. **Base model zoo (14 models):** 4 XGBoost variants (HyperDrive-tuned, shallow, deep,
   regularized), 2 Random Forests, Gradient Boosting, Ridge, 4 deterministic baselines
   (last-month, EWM, rolling-3/6), plus ratio- and residual-ML.
2. **Pair-specific meta-features:** model disagreement (spread), historical error
   profiles, volatility (CV), trend, cross-sectional share features.
3. **Stacked generalization:** two XGBoost stackers (raw + log space, blended 50/50)
   learn *which base model to trust* for each pair type.
4. **Online bias correction:** tracks per-pair error direction across months.
5. **Confidence-weighted blending:** blends toward the EWM baseline when base models
   disagree sharply; caps predictions at 5× historical max.

### Results (Sep–Dec 2025 backtest, 340 pairs ≥ $1K/month)

| Metric | Value |
|--------|-------|
| R² | **0.95** |
| Portfolio error | **−6.8%** |
| CB dollars within ±10% | **85.5%** |
| CB dollars within ±15% | 93.7% |
| Forward-prediction error (Jan 2026, stacker) | **−1.6%** |

---

## The accrual model — and validating it

The Excel tab recomputes the finance team's accrual model from raw data. To trust it, I
validated the output cell-by-cell against the team's existing workbook ("golden file")
across Mar–Dec 2025.

**Finding:** matched within **~1% on accrual and ~0.1–0.9pp on cumulative YTD gap** for
every fully-matured month. Recent months appeared to diverge 30%+ — but root-causing
showed this was **not a model error**: chargebacks *mature over ~2 months* as they're
processed, so the latest months are structurally incomplete. (Proof: the golden file's
single-product November CB exceeded our entire-portfolio November total — impossible
unless it counted later-processed chargebacks attributed to the activity month.)

The dashboard handles this with a **"data complete through" cutoff** that flags immature
months as partial and excludes them from the headline KPIs, so recent months never show
misleading false errors.

---

## Tech stack

| Component | Technology |
|-----------|-----------|
| Framework | Dash (Plotly) + dash-bootstrap-components |
| Charts | Plotly (`plotly_dark`, custom palette) |
| Data | pandas / numpy / openpyxl / pyarrow |
| Storage | SQLite + parquet (local) → Azure Blob + Postgres (prod) |
| Tests | pytest (37 tests) |
| Deploy | Docker → Azure Container Apps |

## Quick start

```bash
pip install -r requirements.txt
python3 app.py            # http://localhost:8050
python3 -m pytest -q      # run the test suite
```

## Uploading data

Type is auto-detected from columns:

| File | Required columns |
|------|------------------|
| Gross Sales | `Shipped Date`, `Shipped Quantity`, `NDC Number` |
| CB Detail | `Process Date`, `Chargeback Quantity`, `Chargeback Amount`, `NDC Number`, `Wholesaler Name` |
| V7 results | `Agreement_norm`, `SKU_norm`, `month`, `pred_v7_final`, `actual` |

Raw transaction files **append with dedup**; `v7_results.csv` **replaces** the ML
dataset (it is a full backtest). The Excel tab needs ≥3 months of history (`Est CB%`
uses the two prior months).

## Architecture

```
app.py                 # Dash layout + callbacks
assets/custom.css      # Dark theme design system
models/excel_model.py  # accrual + wholesaler breakdown + top-N contract filter
models/ml_model.py     # V7 results → pair / product / tier / monthly frames
components/            # header, upload, kpi_cards, tables, charts, filters, render
utils/                 # mappings (NDC→product), storage (pluggable), format
tests/                 # pytest suite (golden-parity, aggregation, cutoff, mappings)
scripts/               # golden-file validation + diagnostics
docs/superpowers/      # design spec + implementation plan
```

## Notes

- **No authentication (MVP).** Displays financial data — add a password gate or Entra
  ID SSO before exposing on any public URL.
- **Pluggable storage.** `STORAGE_BACKEND=local` (SQLite + parquet) for dev;
  `azure` (Blob + Postgres) is the planned prod backend.
- **Deployment** is Docker → Azure Container Apps (`az acr build` → `az containerapp
  update`); note Container App local disk is ephemeral, so use the Azure storage backend
  for durable upload history.

## Highlights for reviewers

- **Test-driven** model layer validated against a known-correct reference.
- **Root-cause analysis** of a 30% apparent error traced to chargeback maturation, not a bug.
- **Honest UI** — immature data is flagged and excluded from KPIs, never shown as false error.
