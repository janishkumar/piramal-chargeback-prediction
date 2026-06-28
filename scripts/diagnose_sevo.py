"""Phase 1 evidence: compare each accrual INPUT against golden, month by month.

Isolates which of {Sales Qty, Est CB %, Avg CB/Unit} diverges, for two products.
"""
import os, sys, warnings
import pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/janish/Desktop/piramal-dashboard")
from models.excel_model import compute_accrual

DL = os.path.expanduser("~/Downloads")
OD = os.path.join(DL, "OneDrive_1_6-28-2026")
GROSS = [os.path.join(OD, "Gross Sales V1.9 0101 3110.xlsx"),
         os.path.join(OD, "Gross_Sales_V1.9_20251101_20251231.xlsx")]
CB = [os.path.join(DL, "Chargeback Detail V2.5 0101 to 3110.xlsx"),
      os.path.join(DL, "Chargeback_Detail_V2.5_20251101_20251231.xlsx")]
GOLDEN = os.path.join(DL, "excel_model_output.xlsx")


def _read(path, markers):
    raw = pd.read_excel(path, header=None, nrows=8)
    hdr = 0
    for i in range(len(raw)):
        if any(m in [str(x) for x in raw.iloc[i].tolist()] for m in markers):
            hdr = i; break
    return pd.read_excel(path, header=hdr)


gross = pd.concat([_read(p, ["Shipped Date"]) for p in GROSS], ignore_index=True)
cb = pd.concat([_read(p, ["Process Date"]) for p in CB], ignore_index=True)
xls = pd.ExcelFile(GOLDEN)

for prod in ["SEVOFLURANE", "ISOFLURANE"]:
    g = pd.read_excel(xls, sheet_name=prod, header=2).dropna(subset=["Month"]).reset_index(drop=True)
    g["Month"] = g["Month"].astype(str)
    out = compute_accrual(gross, cb, prod)
    m = out.merge(g, left_on="year_month", right_on="Month", how="inner")
    print("\n" + "=" * 100)
    print(prod)
    print("=" * 100)
    print(f"{'month':<9}"
          f"{'sales_ours':>12}{'sales_gold':>12}"
          f"{'estpct_our':>11}{'estpct_gld':>11}"
          f"{'cpu_ours':>10}{'cpu_gold':>10}"
          f"{'accr_ours':>13}{'accr_gold':>13}")
    for _, r in m.iterrows():
        print(f"{r['year_month']:<9}"
              f"{r['sales_qty']:>12,.0f}{r['Primary Sales Qty']:>12,.0f}"
              f"{(r['est_cb_pct'] or 0):>11.3f}{r['Est CB Qty %']:>11.3f}"
              f"{(r['avg_cb_per_unit'] or 0):>10.2f}{r['Avg CB Per Unit']:>10.2f}"
              f"{(r['accrual_pred'] or 0):>13,.0f}{r['Accrual']:>13,.0f}")
