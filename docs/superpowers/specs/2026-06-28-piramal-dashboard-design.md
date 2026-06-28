# Piramal US Chargeback Prediction Dashboard — Design Spec

**Date:** 2026-06-28
**Author:** Janish Kumar (ROI by Practus)
**Status:** Approved for planning

This spec resolves the gaps in `Piramal_Dashboard_PRD.md`. The PRD remains the
source of truth for visual/styling detail (Section 3 design system, layouts).
This document overrides the PRD wherever they conflict, and records the
architecture decisions and data-grounded interpretations made during review.

---

## 1. Scope & Architecture

Two-tab Dash dashboard. The two tabs ingest data differently:

- **Excel Model tab = compute-on-upload.** `models/excel_model.py` runs the
  accrual formula from raw **Gross Sales + CB Detail** files. The dashboard
  computes the numbers; it does not read a precomputed Excel.
- **ML Model tab = viewer.** `models/ml_model.py` reads precomputed
  `v7_results.csv` (and optional `predictions_{month}_v7.csv`). The V7 model is
  trained/run in the Azure ML notebook, **never** in the dashboard.

`excel_model_output.xlsx` is used only as a **golden-reference test fixture**
(per-product regression parity), not a runtime input.

Folder structure follows PRD §4 (app.py, assets/, models/, components/, data/,
utils/, Dockerfile, requirements.txt, README.md).

## 2. Data Model — Incremental Append

The dashboard maintains a **cumulative server-side dataset** that grows as
monthly files are uploaded.

- **Raw transaction files append, with dedup on natural keys** to prevent
  double-counting overlapping uploads:
  - **CB Detail** → dedup on `Chargeback Number` + `Line Number`
  - **Gross Sales** → dedup on `Invoice Number` + `Line Number` + `Order Number`
- **`v7_results.csv` is a full backtest → replace, not append.** Appending would
  duplicate pairs. Latest upload replaces the ML dataset.
- The Excel formula needs ≥2 prior months; the cumulative store provides this
  history across uploads, so any single monthly upload need not contain history.

## 3. Storage — Pluggable Backend

`utils/storage.py` exposes one interface with two implementations, selected by
env var (`STORAGE_BACKEND=local|azure`):

- **`local`** (dev/test): filesystem under `data/` + SQLite.
- **`azure`** (prod): Azure Blob for files + Azure Database for PostgreSQL
  (Flexible Server) for metadata.

This lets us build and test now without waiting on Azure provisioning, and
deploy to Blob + managed DB without code changes.

Schema = PRD §10 (`sessions`, `uploaded_files`, `results_cache`) plus a
`data_facts`/cumulative-transaction store holding the deduped raw rows that back
the incremental-append model.

## 4. Data Normalization & Joins (grounded in real files)

- **NDC normalization** (`utils/mappings.py`): strip non-digits and coerce;
  values that are non-numeric (e.g. `'PIR030'` observed in CB Detail) or not in
  `NDC_TO_PROD` map to an **`"UNMAPPED"`** bucket that is surfaced in the UI —
  never silently dropped.
- **Agreement → Wholesaler**: confirmed `Agreement_norm` == CB Detail
  `Contract Number` (173/182 v7 agreements match, 95%). Group CB Detail by
  `Contract Number`, take the **dominant (modal) `Wholesaler Name`** per
  contract (PRD §15.4), classify via `classify_wholesaler`, join to v7 on
  `Agreement_norm`.
- **Month derivation**: `month = YYYY-MM` from `Shipped Date` (Gross Sales) and
  `Process Date` (CB Detail). v7 `month` is already `YYYY-MM`.

## 5. Excel Model Tab — Spec

### 5.1 Formula (per product group, per month)
```
Est_CB_Pct      = (CB_qty[i-1] + CB_qty[i]) / (Sales_qty[i-2] + Sales_qty[i-1])
Est_CB_Qty      = Sales_Qty[i] * Est_CB_Pct
Avg_CB_Per_Unit = SUMPRODUCT(vol_share[i], cpu[i]) * (1 + adj_factor[i])
Accrual         = Est_CB_Qty * Avg_CB_Per_Unit
```
First predictable month = month 3 (needs 2 priors).

### 5.2 Accrual table — match golden file exactly
Column names/order taken verbatim from `excel_model_output.xlsx` product sheets:

`Month | Primary Sales Qty | Est CB Qty % | Est CB Qty | Avg CB Per Unit |
Accrual | Actual CB Qty | Actual CB Qty% | Actual CB / Unit | Actual CB $ |
YTD GAP | YTD Gap %`

- **`Est CB Qty %`** = Est CB Qty ÷ Primary Sales Qty.
- **`YTD GAP` is CUMULATIVE** (verified against golden file):
  `YTD GAP[m]` = Σ(Accrual through m) − Σ(Actual CB $ through m)`.
- **`YTD Gap %`** = cumulative gap ÷ cumulative accrual.
  (Verified: Mar+Apr cum accrual 10,819,247 − cum actual 10,706,047 = 113,199 =
  Apr YTD GAP cell; 113,199 / 10,819,247 = 0.01046 = Apr YTD Gap % cell.)
- No separate per-month gap column (golden file has none).

### 5.3 "Secondary/Primary Vol %" (PRD §7.4 summary table)
Resolved as **CB qty ÷ Sales qty** for the month (the CB-to-sales volume ratio).

### 5.4 `adj_factor` UI (PRD called it configurable but gave no control)
Per-month editable inputs above the accrual table, default 0, persisted per
session. Feeds the `(1 + adj_factor)` term in Avg_CB_Per_Unit.

### 5.5 Chargeback-lag handling
A "data complete through" cutoff month. Months after the cutoff are rendered
greyed / marked "partial" so incomplete recent actuals don't show as huge fake
errors. Cutoff defaults to the latest fully-closed CB month; user-overridable.

### 5.6 Other sections
KPI cards (§7.3), Primary Sales vs CB summary (§7.4), Wholesaler volume-share &
CB/unit tables (§7.5), monthly accuracy bar+line chart (§7.7) — per PRD.

## 6. ML Model Tab — Spec

- **Columns available** (superset of PRD §8.1): `Agreement_norm`, `SKU_norm`,
  `month`, `pred_v7_stacker`, `pred_v7_corrected`, `pred_v7_final`,
  `pred_global`, `pred_last_month`, `pred_ewm`, `pred_meta`, `actual`. Primary
  prediction = `pred_v7_final`; baseline = `pred_ewm`; comparison = `pred_global`.
- **Product aggregation**: sum preds & actuals per product-month; error computed
  from the sums, not averaged pair errors (PRD §15.3).
- **Wholesaler column** via §4 dominant-contract mapping.
- Product-level view, pair-level view, error histogram, business-tier breakdown —
  per PRD §8.4–§8.6.

## 7. Cross-Cutting

### 7.1 Unified thresholds (PRD mixed three schemes)
- **Status bands** (pair/product status chips): GOOD ≤10% / OK ≤20% / BAD >20%.
- **KPI error-% coloring**: green ≤5% / yellow ≤15% / red >15%.
- **Tier table** keeps its <10 / <15 / <20 / >30 reporting columns (these are
  reporting buckets, not status bands).

### 7.2 Formatting
Shared helpers: dollars `$X,XXX,XXX`, percentages `X.X%`. Charts use Plotly
`plotly_dark` themed to the §3 palette.

### 7.3 Auth
**None for MVP** (deliberate deferral). README documents the data-exposure risk
and recommends adding a password gate or Entra Easy Auth before wider sharing.

### 7.4 Independent tabs
Excel tab works with only Gross Sales + CB Detail; ML tab works with only
`v7_results.csv`. Each shows an upload-prompt empty state when its data is
absent (PRD §15.10).

## 8. Testing Strategy (TDD)

Tests written before implementation:

- **`models/excel_model.py`**: parity test vs `excel_model_output.xlsx` for each
  product (Accrual, Est CB Qty, YTD GAP, YTD Gap % within tolerance).
- **`models/ml_model.py`**: product-aggregation-from-sums, tier breakdown math,
  pair error/status classification, dominant-wholesaler mapping.
- **`utils/mappings.py`**: NDC normalization (incl. `'PIR030'` → UNMAPPED),
  wholesaler classification, Agreement→Contract join coverage.
- **`utils/storage.py`**: append+dedup idempotency on overlapping uploads;
  v7 replace-not-append.

## 9. Out of Scope (MVP)

- Running/training the V7 model in-app.
- Authentication / multi-user isolation.
- Forward-prediction generation (only displays uploaded `predictions_*` CSVs).
- Mobile-first design (responsive degradation only, per PRD §11).

## 10. Reference Data Locations (dev)

Sample files present in `~/Downloads/` for building & testing:
`v7_results.csv`, `predictions_2026-01_v7.csv`, `excel_model_output.xlsx`
(golden), `Chargeback_Detail_V2.5_*.xlsx`, `Nov_Dec_Gross_Sales_For_Paste.xlsx`,
`V7_Accuracy_Report.xlsx`.
