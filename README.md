# Piramal US Chargeback Prediction Dashboard

Interactive dashboard for Piramal Critical Care's chargeback (CB) prediction
system. Two tabs:

- **Excel Model** — replicates the *CB Forecast Model (3)* accrual logic,
  computed in-app from raw Gross Sales + CB Detail uploads:
  `Accrual = Sales Qty × Est CB% × Avg CB Per Unit`. YTD Gap is cumulative.
- **ML Model** — displays V7 stacked-generalization predictions from a
  precomputed `v7_results.csv`, at pair (Agreement × SKU) and product level.

The V7 model is trained/run in the Azure ML notebook; this dashboard is a
**viewer** for its outputs (it does not train or predict).

## Quick start (local)

```bash
pip install -r requirements.txt
python3 app.py            # http://localhost:8050
```

Run tests (uses sample files in `~/Downloads`, skips any that are absent):

```bash
python3 -m pytest -q
```

## Uploading data

Drag files onto the upload panel. Type is auto-detected from columns:

| File | Required columns | Detected as |
|------|------------------|-------------|
| Gross Sales | `Shipped Date`, `Shipped Quantity`, `NDC Number` | `gross_sales` |
| CB Detail | `Process Date`, `Chargeback Quantity`, `Chargeback Amount`, `NDC Number`, `Wholesaler Name` | `cb_detail` |
| V7 results | `Agreement_norm`, `SKU_norm`, `month`, `pred_v7_final`, `actual` | `v7_results` |

Raw transaction files **append with dedup** (CB on `Chargeback Number`+`Line
Number`; Gross on `Invoice Number`+`Line Number`+`Order Number`).
`v7_results.csv` **replaces** the ML dataset (it is a full backtest).

> **Excel tab needs ≥3 months of history.** `Est CB%` uses the two prior
> months, so the first predictable month is month 3. Uploading only 1–2 months
> shows `$0` accrual — this is expected, not a bug.

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `DATA_ROOT` | `./data` | Where uploads, results, and `db.sqlite` live (local backend) |
| `STORAGE_BACKEND` | `local` | `local` (SQLite + pickle facts). `azure` (Blob + Postgres) is the planned prod backend — interface is in place, implementation is a follow-up. |

## ⚠️ Security note — no authentication (MVP)

This MVP ships with **no authentication**. It displays pharma chargeback
financials, so do **not** expose it on a public URL without a gate. Before
sharing beyond a trusted internal network, add one of:

- A shared-password / basic-auth proxy, or
- Azure Container Apps **Easy Auth** (Entra ID SSO).

## Deployment (Azure Container Apps)

```bash
# Build & push to Azure Container Registry
az acr build --registry piramalacr --image piramal-dashboard:v2 .

# Update the existing Container App (piramal-dashboard / piramal-rg / East US)
az containerapp update \
  --name piramal-dashboard \
  --resource-group piramal-rg \
  --image piramalacr.azurecr.io/piramal-dashboard:v2
```

> Container App local disk is **ephemeral** — uploads and `db.sqlite` are lost
> on restart/scale. For durable history, switch `STORAGE_BACKEND=azure` (Blob +
> Postgres) or mount an Azure Files share at `DATA_ROOT`.

## Project layout

```
app.py                 # Dash layout + callbacks
assets/custom.css      # Dark theme (design system)
models/excel_model.py  # Accrual computation
models/ml_model.py     # V7 results processing
components/            # header, upload, kpi_cards, tables, charts, filters, render
utils/                 # mappings, ingest, storage, format
tests/                 # pytest suite (golden-parity + integration)
docs/superpowers/      # design spec + implementation plan
```
