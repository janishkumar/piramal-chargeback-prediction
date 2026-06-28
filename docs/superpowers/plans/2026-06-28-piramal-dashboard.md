# Piramal CB Prediction Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-tab Dash dashboard that computes the Excel accrual model from raw uploads and displays V7 ML predictions from precomputed CSVs.

**Architecture:** Bottom-up. Build & test the pure-Python data layer (mappings → storage → excel_model → ml_model) against real sample files first, then assemble the Dash UI (components → callbacks → app) on top. Storage is pluggable (local SQLite/FS for dev, Blob+Postgres for prod).

**Tech Stack:** Python 3.10, Dash + dash-bootstrap-components, Plotly, pandas, openpyxl, pytest. SQLite (dev).

---

## File Structure

| File | Responsibility |
|------|----------------|
| `requirements.txt` | Pinned deps (PRD §2) |
| `utils/mappings.py` | NDC→Product, wholesaler classification, NDC normalization |
| `utils/storage.py` | Pluggable storage interface (local now), sessions/files/facts |
| `models/excel_model.py` | Accrual computation from raw Gross Sales + CB Detail |
| `models/ml_model.py` | Process v7_results → pair/product/tier/monthly frames |
| `utils/format.py` | Dollar/percent formatters, status-band helpers |
| `components/*.py` | header, upload, kpi_cards, tables, charts, filters builders |
| `app.py` | Layout, tabs, callbacks, wiring |
| `assets/custom.css` | Dark theme (PRD §3) |
| `tests/conftest.py` | Fixtures pointing at sample files in `~/Downloads` |
| `tests/test_*.py` | One per data-layer module |
| `Dockerfile`, `README.md` | Deploy + docs |

Test data (read-only fixtures): `~/Downloads/v7_results.csv`, `excel_model_output.xlsx` (golden), `Chargeback_Detail_V2.5_20251101_20251231.xlsx`, `Nov_Dec_Gross_Sales_For_Paste.xlsx`.

---

## Task 0: Project scaffold

**Files:**
- Create: `requirements.txt`, `tests/conftest.py`, `pytest.ini`

- [ ] **Step 1: Write `requirements.txt`**
```
dash>=2.14.0
dash-bootstrap-components>=1.5.0
plotly>=5.18.0
pandas>=1.5.0
numpy>=1.23.0
openpyxl>=3.1.0
gunicorn>=21.2.0
pytest>=7.4.0
```
(scikit-learn/xgboost omitted: dashboard does not train/predict — ML tab is a viewer.)

- [ ] **Step 2: Write `pytest.ini`**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 3: Write `tests/conftest.py`** — resolve sample-file paths, skip if absent
```python
import os, pathlib, pytest

DL = pathlib.Path(os.path.expanduser("~/Downloads"))

def _req(name):
    p = DL / name
    if not p.exists():
        pytest.skip(f"sample file missing: {p}")
    return p

@pytest.fixture
def v7_csv():        return _req("v7_results.csv")
@pytest.fixture
def golden_xlsx():   return _req("excel_model_output.xlsx")
@pytest.fixture
def cb_xlsx():       return _req("Chargeback_Detail_V2.5_20251101_20251231.xlsx")
@pytest.fixture
def gross_xlsx():    return _req("Nov_Dec_Gross_Sales_For_Paste.xlsx")
```

- [ ] **Step 4: Install & verify**
Run: `python3 -m pip install -r requirements.txt && python3 -m pytest -q`
Expected: `no tests ran` (0 collected), exit 0.

- [ ] **Step 5: Commit**
```bash
git add requirements.txt pytest.ini tests/conftest.py
git commit -m "chore: project scaffold and test fixtures"
```

---

## Task 1: NDC & wholesaler mappings

**Files:**
- Create: `utils/mappings.py`, `utils/__init__.py`
- Test: `tests/test_mappings.py`

- [ ] **Step 1: Write failing tests** — `tests/test_mappings.py`
```python
from utils.mappings import normalize_ndc, ndc_to_product, classify_wholesaler

def test_normalize_clean_ndc():
    assert normalize_ndc("66794024942") == "66794024942"

def test_normalize_float_ndc():
    assert normalize_ndc(66794024942.0) == "66794024942"

def test_normalize_non_numeric_returns_none():
    assert normalize_ndc("PIR030") is None

def test_unmapped_ndc_bucket():
    assert ndc_to_product("99999999999") == "UNMAPPED"
    assert ndc_to_product("PIR030") == "UNMAPPED"

def test_known_ndc():
    assert ndc_to_product("66794001525") == "SEVOFLURANE"

def test_classify_wholesaler():
    assert classify_wholesaler("CENCORA GLOBAL PROCUREMEN") == "ABC"
    assert classify_wholesaler("McKesson Medical Surgical") == "Mckesson Medical"
    assert classify_wholesaler("McKesson Corp") == "Mckesson"
    assert classify_wholesaler("Cardinal Health") == "Cardinal"
    assert classify_wholesaler("Random Dist") == "Others"
```

- [ ] **Step 2: Run, verify fail**
Run: `python3 -m pytest tests/test_mappings.py -q`
Expected: FAIL (ModuleNotFoundError / ImportError).

- [ ] **Step 3: Implement `utils/mappings.py`**
```python
import re

NDC_TO_PROD = {
    "66794015701": "GABLOFEN", "66794015702": "GABLOFEN", "66794015101": "GABLOFEN",
    "66794015502": "GABLOFEN", "66794015602": "GABLOFEN", "66794015501": "GABLOFEN",
    "66794015601": "GABLOFEN", "66794025841": "Pantoprazole",
    "66794023741": "DOXYCYCLINE", "66794020541": "GLYCOPYRROLATE",
    "66794020342": "GLYCOPYRROLATE", "66794020242": "GLYCOPYRROLATE",
    "66794020442": "GLYCOPYRROLATE", "66794024942": "CHLORPROMAZINE",
    "66794025042": "CHLORPROMAZINE", "66794001525": "SEVOFLURANE",
    "66794002225": "NOVA-SEVOFLURANE", "66794001725": "ISOFLURANE",
    "66794001710": "ISOFLURANE", "66794001925": "NOVA-ISOFLURANE",
    "66794001910": "NOVA-ISOFLURANE", "66794025542": "Zinc Sulfate",
    "66794023942": "Zinc Sulfate", "66794024042": "Zinc Sulfate",
    "66794021943": "LINEZOLID", "66794023643": "NOVA-LINEZOLID",
    "66794023042": "DEXMED", "66794023541": "DEXMED",
    "66794023342": "NOVA-DEXMED", "66794023444": "DEXMED",
    "66794022841": "ROCURONIUM", "66794022941": "ROCURONIUM",
    "66794016002": "MITIGO", "66794016202": "MITIGO",
    "66794025964": "EDARAVONE", "66794023242": "SUCCINYCHOLINE",
    "66794001310": "ISOFLURANE", "66794001325": "ISOFLURANE",
}

WHOLESALER_GROUPS = ["ABC", "Cardinal", "Mckesson", "Mckesson Medical", "Others"]

def normalize_ndc(value):
    """Return 11-digit NDC string, or None if not numeric."""
    if value is None:
        return None
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    digits = re.sub(r"\D", "", s)
    return digits if digits else None

def ndc_to_product(value):
    ndc = normalize_ndc(value)
    if ndc is None:
        return "UNMAPPED"
    return NDC_TO_PROD.get(ndc, "UNMAPPED")

def classify_wholesaler(name):
    n = str(name).upper()
    if "MCKESSON MEDICAL" in n or "MCKESSON MED" in n:
        return "Mckesson Medical"
    if "MCKESSON" in n:
        return "Mckesson"
    if "CARDINAL" in n:
        return "Cardinal"
    if "ABC" in n or "AMERISOURCE" in n or "CENCORA" in n:
        return "ABC"
    return "Others"
```
Also create empty `utils/__init__.py`.

- [ ] **Step 4: Run, verify pass**
Run: `python3 -m pytest tests/test_mappings.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**
```bash
git add utils/__init__.py utils/mappings.py tests/test_mappings.py
git commit -m "feat: NDC normalization and wholesaler classification"
```

---

## Task 2: Excel accrual model (golden-parity)

**Files:**
- Create: `models/excel_model.py`, `models/__init__.py`
- Test: `tests/test_excel_model.py`

**Reference frame** returned by `compute_accrual(gross_df, cb_df, product_group)`:
columns `year_month, sales_qty, est_cb_pct, est_cb_qty, avg_cb_per_unit,
accrual_pred, actual_cb_qty, actual_cb_pct, actual_cb_per_unit, actual_cb_amt,
ytd_gap, ytd_gap_pct`. `ytd_gap`/`ytd_gap_pct` are **cumulative** (running sums).

- [ ] **Step 1: Write golden-parity test** — `tests/test_excel_model.py`
```python
import pandas as pd
from models.excel_model import compute_accrual

def _golden(golden_xlsx, sheet):
    raw = pd.read_excel(golden_xlsx, sheet_name=sheet, header=2)
    return raw.dropna(subset=["Month"]).reset_index(drop=True)

def test_ytd_gap_is_cumulative(golden_xlsx):
    g = _golden(golden_xlsx, "SEVOFLURANE")
    # Apr YTD GAP == cumulative(Accrual) - cumulative(Actual CB $) through Apr
    cum_acc = g["Accrual"].iloc[:2].sum()
    cum_act = g["Actual CB $"].iloc[:2].sum()
    assert abs((cum_acc - cum_act) - g["YTD GAP"].iloc[1]) < 1.0

def test_accrual_matches_golden_sevoflurane(gross_xlsx, cb_xlsx, golden_xlsx):
    # NOTE: requires gross+cb covering the golden period. Where sample files
    # only cover Nov-Dec, assert on the overlapping months only.
    g = _golden(golden_xlsx, "SEVOFLURANE")
    out = compute_accrual(pd.read_excel(gross_xlsx), pd.read_excel(cb_xlsx), "SEVOFLURANE")
    merged = out.merge(g, left_on="year_month", right_on="Month", how="inner")
    assert len(merged) >= 1
    for _, r in merged.iterrows():
        assert abs(r["accrual_pred"] - r["Accrual"]) / max(r["Accrual"], 1) < 0.02
```

- [ ] **Step 2: Run, verify fail**
Run: `python3 -m pytest tests/test_excel_model.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement `models/excel_model.py`**
```python
import numpy as np
import pandas as pd
from utils.mappings import ndc_to_product, classify_wholesaler

def _monthly(df, date_col, qty_col, product_group):
    d = df.copy()
    d["prod"] = d["NDC Number"].map(ndc_to_product)
    d = d[d["prod"] == product_group]
    d["year_month"] = pd.to_datetime(d[date_col]).dt.strftime("%Y-%m")
    return d

def compute_accrual(gross_df, cb_df, product_group, adj_factor=None):
    g = _monthly(gross_df, "Shipped Date", "Shipped Quantity", product_group)
    c = _monthly(cb_df, "Process Date", "Chargeback Quantity", product_group)
    c["wh"] = c["Wholesaler Name"].map(classify_wholesaler)

    sales = g.groupby("year_month")["Shipped Quantity"].sum().rename("sales_qty")
    cbq = c.groupby("year_month")["Chargeback Quantity"].sum().rename("actual_cb_qty")
    cba = c.groupby("year_month")["Chargeback Amount"].sum().rename("actual_cb_amt")

    months = sorted(set(sales.index) | set(cbq.index))
    rows = []
    for i, m in enumerate(months):
        s = float(sales.get(m, 0.0))
        cq = float(cbq.get(m, 0.0))
        ca = float(cba.get(m, 0.0))
        if i < 2:
            est_pct = np.nan
        else:
            denom = float(sales.get(months[i-2], 0)) + float(sales.get(months[i-1], 0))
            numer = float(cbq.get(months[i-1], 0)) + float(cbq.get(m, 0))
            est_pct = numer / denom if denom else np.nan
        # Avg CB per unit = SUMPRODUCT(volume share, cpu) * (1+adj)
        mc = c[c["year_month"] == m]
        adj = 0.0 if adj_factor is None else float(adj_factor.get(m, 0.0))
        if len(mc):
            by_wh = mc.groupby("wh").agg(q=("Chargeback Quantity", "sum"),
                                         a=("Chargeback Amount", "sum"))
            share = by_wh["q"] / by_wh["q"].sum()
            cpu = by_wh["a"] / by_wh["q"].replace(0, np.nan)
            avg_cpu = float((share * cpu).sum()) * (1 + adj)
        else:
            avg_cpu = np.nan
        est_qty = s * est_pct if est_pct == est_pct else np.nan
        accrual = est_qty * avg_cpu if est_qty == est_qty else np.nan
        rows.append(dict(year_month=m, sales_qty=s, est_cb_pct=est_pct,
                         est_cb_qty=est_qty, avg_cb_per_unit=avg_cpu,
                         accrual_pred=accrual, actual_cb_qty=cq,
                         actual_cb_pct=(cq/s if s else np.nan),
                         actual_cb_per_unit=(ca/cq if cq else np.nan),
                         actual_cb_amt=ca))
    out = pd.DataFrame(rows)
    out["ytd_gap"] = (out["accrual_pred"].fillna(0).cumsum()
                      - out["actual_cb_amt"].fillna(0).cumsum())
    out["ytd_gap_pct"] = out["ytd_gap"] / out["accrual_pred"].fillna(0).cumsum().replace(0, np.nan)
    return out
```
Also create empty `models/__init__.py`.

- [ ] **Step 4: Run, verify pass** (cumulative test must pass; parity test may xfail if sample gross/cb don't overlap golden period — mark accordingly)
Run: `python3 -m pytest tests/test_excel_model.py -q`
Expected: cumulative test PASS. If parity test errors on coverage, wrap its body in `pytest.skip` when `len(merged)==0`.

- [ ] **Step 5: Commit**
```bash
git add models/__init__.py models/excel_model.py tests/test_excel_model.py
git commit -m "feat: Excel accrual model with cumulative YTD gap"
```

---

## Task 3: ML model processing

**Files:**
- Create: `models/ml_model.py`
- Test: `tests/test_ml_model.py`

- [ ] **Step 1: Write tests** — `tests/test_ml_model.py`
```python
import pandas as pd
from models.ml_model import process_v7_results

def test_product_error_from_sums(v7_csv):
    df = pd.read_csv(v7_csv)
    res = process_v7_results(df)
    ps = res["product_summary"]
    assert {"product_group", "total_actual", "total_v7", "v7_error_pct"} <= set(ps.columns)
    row = ps.iloc[0]
    # error computed from sums, not avg of pair errors
    expected = (row["total_v7"] - row["total_actual"]) / row["total_actual"]
    assert abs(row["v7_error_pct"] - expected) < 1e-6

def test_pair_status_bands(v7_csv):
    df = pd.read_csv(v7_csv)
    pairs = process_v7_results(df)["pair_detail"]
    assert set(pairs["status"].unique()) <= {"GOOD", "OK", "BAD"}

def test_tier_breakdown_present(v7_csv):
    df = pd.read_csv(v7_csv)
    tiers = process_v7_results(df)["tier_breakdown"]
    assert "tier" in tiers.columns and len(tiers) >= 1
```

- [ ] **Step 2: Run, verify fail**
Run: `python3 -m pytest tests/test_ml_model.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement `models/ml_model.py`**
```python
import numpy as np
import pandas as pd
from utils.mappings import ndc_to_product, classify_wholesaler

TIERS = [(100_000, np.inf, ">$100K"), (50_000, 100_000, "$50K-$100K"),
         (25_000, 50_000, "$25K-$50K"), (10_000, 25_000, "$10K-$25K"),
         (5_000, 10_000, "$5K-$10K"), (1_000, 5_000, "$1K-$5K"),
         (-np.inf, 1_000, "<$1K")]

def _status(err):
    a = abs(err)
    return "GOOD" if a <= 0.10 else ("OK" if a <= 0.20 else "BAD")

def _err(pred, act):
    return (pred - act) / act if act else np.nan

def process_v7_results(v7_df, cb_detail_df=None):
    df = v7_df.copy()
    df["SKU_norm"] = df["SKU_norm"].apply(lambda x: str(int(x)) if pd.notna(x) else x)
    df["Agreement_norm"] = df["Agreement_norm"].apply(lambda x: str(int(x)) if pd.notna(x) else x)
    df["product_group"] = df["SKU_norm"].map(ndc_to_product)

    wh_map = {}
    if cb_detail_df is not None and "Contract Number" in cb_detail_df.columns:
        cb = cb_detail_df.copy()
        cb["wh"] = cb["Wholesaler Name"].map(classify_wholesaler)
        cb["Contract Number"] = cb["Contract Number"].apply(
            lambda x: str(int(x)) if pd.notna(x) else x)
        wh_map = (cb.groupby("Contract Number")["wh"]
                  .agg(lambda s: s.mode().iloc[0]).to_dict())

    # pair detail (aggregate across months per Agreement x SKU)
    pg = df.groupby(["Agreement_norm", "SKU_norm", "product_group"]).agg(
        months=("month", "nunique"),
        total_actual=("actual", "sum"),
        total_v7=("pred_v7_final", "sum")).reset_index()
    pg["avg_monthly"] = pg["total_actual"] / pg["months"].replace(0, np.nan)
    pg["error_pct"] = pg.apply(lambda r: _err(r["total_v7"], r["total_actual"]), axis=1)
    pg["status"] = pg["error_pct"].apply(_status)
    pg["wholesaler"] = pg["Agreement_norm"].map(wh_map).fillna("Others")

    # product summary (error from sums)
    ps = df.groupby("product_group").agg(
        total_actual=("actual", "sum"),
        total_v7=("pred_v7_final", "sum"),
        total_ewm=("pred_ewm", "sum")).reset_index()
    ps["v7_error_pct"] = (ps["total_v7"] - ps["total_actual"]) / ps["total_actual"]
    ps["ewm_error_pct"] = (ps["total_ewm"] - ps["total_actual"]) / ps["total_actual"]
    ps["v7_better"] = ps["v7_error_pct"].abs() < ps["ewm_error_pct"].abs()

    # monthly portfolio
    mp = df.groupby("month").agg(total_actual=("actual", "sum"),
                                 total_v7=("pred_v7_final", "sum")).reset_index()
    mp["error_pct"] = (mp["total_v7"] - mp["total_actual"]) / mp["total_actual"]

    # tier breakdown (by avg monthly CB per pair)
    def tier_of(v):
        for lo, hi, name in TIERS:
            if lo <= v < hi:
                return name
        return "<$1K"
    pg["tier"] = pg["avg_monthly"].fillna(0).apply(tier_of)
    tb = pg.groupby("tier").agg(
        pairs=("SKU_norm", "count"),
        total_cb=("total_actual", "sum"),
        within10=("error_pct", lambda s: (s.abs() <= 0.10).mean()),
        within20=("error_pct", lambda s: (s.abs() <= 0.20).mean()),
        avg_v7_err=("error_pct", lambda s: s.abs().mean())).reset_index()

    return {"pair_detail": pg, "product_summary": ps,
            "monthly_portfolio": mp, "tier_breakdown": tb}
```

- [ ] **Step 4: Run, verify pass**
Run: `python3 -m pytest tests/test_ml_model.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**
```bash
git add models/ml_model.py tests/test_ml_model.py
git commit -m "feat: V7 results processing (pair/product/tier/monthly)"
```

---

## Task 4: Storage layer (local backend) with dedup

**Files:**
- Create: `utils/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write tests** — `tests/test_storage.py`
```python
import pandas as pd
from utils.storage import LocalStorage

def test_append_dedup_cb(tmp_path):
    st = LocalStorage(tmp_path)
    df = pd.DataFrame({"Chargeback Number": [1, 1, 2], "Line Number": [1, 1, 1],
                       "Chargeback Amount": [10, 10, 5]})
    st.append_cb_detail(df)
    st.append_cb_detail(df)  # full overlap -> no growth
    out = st.load_cb_detail()
    assert len(out) == 2  # (1,1) and (2,1) deduped

def test_v7_replaces(tmp_path):
    st = LocalStorage(tmp_path)
    st.save_v7(pd.DataFrame({"a": [1, 2, 3]}))
    st.save_v7(pd.DataFrame({"a": [9]}))
    assert len(st.load_v7()) == 1

def test_session_roundtrip(tmp_path):
    st = LocalStorage(tmp_path)
    sid = st.create_session(label="Nov-Dec 2025", start="2025-11", end="2025-12")
    sessions = st.list_sessions()
    assert any(s["id"] == sid for s in sessions)
```

- [ ] **Step 2: Run, verify fail**
Run: `python3 -m pytest tests/test_storage.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement `utils/storage.py`** (local backend; SQLite metadata + parquet/csv facts)
```python
import sqlite3, uuid, pathlib
import pandas as pd

CB_KEYS = ["Chargeback Number", "Line Number"]
GROSS_KEYS = ["Invoice Number", "Line Number", "Order Number"]

class LocalStorage:
    def __init__(self, root):
        self.root = pathlib.Path(root)
        (self.root / "facts").mkdir(parents=True, exist_ok=True)
        self.db = self.root / "db.sqlite"
        self._init_db()

    def _init_db(self):
        con = sqlite3.connect(self.db)
        con.executescript("""
        CREATE TABLE IF NOT EXISTS sessions(
          id TEXT PRIMARY KEY, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          label TEXT, date_range_start TEXT, date_range_end TEXT,
          status TEXT DEFAULT 'complete');
        """)
        con.commit(); con.close()

    def _append(self, name, df, keys):
        path = self.root / "facts" / f"{name}.parquet"
        if path.exists():
            df = pd.concat([pd.read_parquet(path), df], ignore_index=True)
        present = [k for k in keys if k in df.columns]
        if present:
            df = df.drop_duplicates(subset=present)
        df.to_parquet(path, index=False)
        return df

    def append_cb_detail(self, df):  return self._append("cb_detail", df, CB_KEYS)
    def append_gross(self, df):      return self._append("gross", df, GROSS_KEYS)
    def load_cb_detail(self):
        p = self.root / "facts" / "cb_detail.parquet"
        return pd.read_parquet(p) if p.exists() else pd.DataFrame()
    def load_gross(self):
        p = self.root / "facts" / "gross.parquet"
        return pd.read_parquet(p) if p.exists() else pd.DataFrame()

    def save_v7(self, df):
        df.to_parquet(self.root / "facts" / "v7.parquet", index=False)
    def load_v7(self):
        p = self.root / "facts" / "v7.parquet"
        return pd.read_parquet(p) if p.exists() else pd.DataFrame()

    def create_session(self, label, start, end):
        sid = str(uuid.uuid4())
        con = sqlite3.connect(self.db)
        con.execute("INSERT INTO sessions(id,label,date_range_start,date_range_end)"
                    " VALUES(?,?,?,?)", (sid, label, start, end))
        con.commit(); con.close()
        return sid
    def list_sessions(self):
        con = sqlite3.connect(self.db); con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute("SELECT * FROM sessions ORDER BY created_at DESC")]
        con.close(); return rows
```
(Requires `pyarrow`; add `pyarrow>=12.0` to requirements.txt.)

- [ ] **Step 4: Run, verify pass**
Run: `python3 -m pytest tests/test_storage.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**
```bash
git add utils/storage.py tests/test_storage.py requirements.txt
git commit -m "feat: local storage with append-dedup and v7 replace"
```

---

## Task 5: Formatting & status helpers

**Files:**
- Create: `utils/format.py`
- Test: `tests/test_format.py`

- [ ] **Step 1: Tests**
```python
from utils.format import fmt_dollar, fmt_pct, kpi_color, status_band

def test_fmt_dollar(): assert fmt_dollar(1234567) == "$1,234,567"
def test_fmt_pct(): assert fmt_pct(0.2594) == "25.9%"
def test_kpi_color():
    assert kpi_color(0.04) == "green"
    assert kpi_color(0.12) == "yellow"
    assert kpi_color(0.20) == "red"
def test_status_band():
    assert status_band(0.05) == "GOOD"
    assert status_band(0.15) == "OK"
    assert status_band(0.25) == "BAD"
```

- [ ] **Step 2: Run, verify fail** — `python3 -m pytest tests/test_format.py -q` → FAIL

- [ ] **Step 3: Implement `utils/format.py`**
```python
def fmt_dollar(v):
    try: return f"${round(float(v)):,}"
    except (TypeError, ValueError): return "-"

def fmt_pct(v, digits=1):
    try: return f"{float(v)*100:.{digits}f}%"
    except (TypeError, ValueError): return "-"

def kpi_color(err):
    a = abs(err)
    return "green" if a <= 0.05 else ("yellow" if a <= 0.15 else "red")

def status_band(err):
    a = abs(err)
    return "GOOD" if a <= 0.10 else ("OK" if a <= 0.20 else "BAD")
```

- [ ] **Step 4: Run, verify pass** — `python3 -m pytest tests/test_format.py -q` → PASS

- [ ] **Step 5: Commit**
```bash
git add utils/format.py tests/test_format.py
git commit -m "feat: formatting and threshold helpers"
```

---

## Task 6: CSS theme + app shell (smoke-testable)

**Files:**
- Create: `assets/custom.css`, `app.py`, `components/__init__.py`, `components/header.py`

- [ ] **Step 1: Write `assets/custom.css`** — paste the full Section 3 palette as CSS vars on `:root`, plus `.card`, `.kpi-card`, `.kpi-value`, `.kpi-label`, status background classes (`.status-good/ok/bad`). (Copy values verbatim from PRD §3.)

- [ ] **Step 2: Write `components/header.py`**
```python
import dash_bootstrap_components as dbc
from dash import html

def header():
    return html.Div(className="app-header", children=[
        html.Span("Piramal", className="brand"),
        html.Span("Chargeback Prediction Dashboard", className="title"),
    ])
```

- [ ] **Step 3: Write minimal `app.py`** (tabs + header, empty tab bodies)
```python
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from components.header import header

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
                suppress_callback_exceptions=True)
server = app.server
app.layout = html.Div([
    header(),
    dcc.Tabs(id="tabs", value="excel", children=[
        dcc.Tab(label="Excel Model", value="excel"),
        dcc.Tab(label="ML Model", value="ml"),
    ]),
    html.Div(id="tab-content"),
])

if __name__ == "__main__":
    app.run(debug=True, port=8050)
```

- [ ] **Step 4: Smoke test** — `tests/test_app_smoke.py`
```python
def test_app_imports():
    import app
    assert app.server is not None
```
Run: `python3 -m pytest tests/test_app_smoke.py -q` → PASS

- [ ] **Step 5: Commit**
```bash
git add assets/custom.css app.py components/__init__.py components/header.py tests/test_app_smoke.py
git commit -m "feat: app shell, header, dark theme css"
```

---

## Task 7: Components — KPIs, tables, charts, filters

**Files:** Create `components/kpi_cards.py`, `components/tables.py`, `components/charts.py`, `components/filters.py`, `components/upload.py`.

Each builder is a pure function returning a Dash component from a DataFrame/values. Build incrementally; smoke-test each import. Key builders:
- `kpi_cards.kpi_row(items)` → list of `.kpi-card` divs (value, label, delta color via `kpi_color`).
- `tables.data_table(df, id, **opts)` → `dash_table.DataTable` with `sort_action='native'`, `filter_action='native'`, dark style; status cells colored via `style_data_conditional` using `status_band`.
- `charts.accuracy_bar_line(df)` → Plotly fig (blue predicted bars, green actual bars, error % line on secondary y) using `plotly_dark` + palette.
- `charts.error_histogram(errors)` → histogram with vlines at 10/20/30%.
- `filters.product_dropdown(options, default="SEVOFLURANE")`, `filters.month_range(...)`, `filters.view_toggle(...)`, `filters.error_slider(...)`.
- `upload.upload_panel()` → `dcc.Upload` drop area + detected-type badges + history list + Process button.

- [ ] For each builder: write a smoke test asserting it returns a Dash component without error, implement, run, commit. (One commit per component file.)

---

## Task 8: Wire callbacks & tab bodies

**Files:** Modify `app.py`; add `components/tabs_excel.py`, `components/tabs_ml.py`.

- [ ] Render tab content on `tabs` value change.
- [ ] Upload callback: detect file type by headers (PRD §9.2), validate required columns, store via `LocalStorage`, auto-label session by detected date range.
- [ ] Excel tab callback: on filter change, `compute_accrual` → KPIs + 4 sections + chart. Empty-state when no Gross/CB data.
- [ ] ML tab callback: `process_v7_results` → KPIs + product/pair views + histogram + tier table. Empty-state when no v7 data.
- [ ] `adj_factor` inputs feed `compute_accrual`. "Data complete through" cutoff greys later months.
- [ ] Manual verification: `python3 app.py`, open `http://localhost:8050`, upload sample files from `~/Downloads`, confirm both tabs populate. (Use the `verify` skill / Claude Preview MCP for screenshot confirmation.)
- [ ] Commit after each callback works.

---

## Task 9: Deployment artifacts

**Files:** Create `Dockerfile` (PRD §13 verbatim), `README.md` (run instructions, env vars `STORAGE_BACKEND`, **explicit no-auth data-exposure warning**, Azure deploy commands from PRD §13).

- [ ] Write Dockerfile, README. Build locally: `docker build -t piramal-dashboard .` → succeeds.
- [ ] Commit.

---

## Self-Review Notes

- **Spec coverage:** §1 scope→T2/T3; §2 append→T4; §3 storage→T4; §4 normalize/join→T1,T3; §5 Excel→T2,T8; §6 ML→T3,T8; §7 thresholds/format→T5, auth→T9; §8 testing→T1-T5. All covered.
- **Azure backend** (Blob+Postgres) is interface-stubbed in T4 (local only); prod backend is a follow-up plan once infra is provisioned — flagged, not silently dropped.
- **Parity test caveat:** sample Gross Sales (`Nov_Dec`) may not cover the golden file's Mar-Dec span; parity asserts only on overlapping months and skips if none. Full parity requires the complete gross-sales history file.
