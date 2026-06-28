"""Phase 3: test which CB date column reproduces golden monthly CB qty."""
import os, sys, warnings
import pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/janish/Desktop/piramal-dashboard")
from utils.mappings import ndc_to_product

DL = os.path.expanduser("~/Downloads")
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


cb = pd.concat([_read(p, ["Process Date"]) for p in CB], ignore_index=True)
cb["prod"] = cb["NDC Number"].map(ndc_to_product)
sub = cb[cb["prod"] == "SEVOFLURANE"].copy()

g = pd.read_excel(GOLDEN, sheet_name="SEVOFLURANE", header=2).dropna(subset=["Month"])
g["Month"] = g["Month"].astype(str)
gold = dict(zip(g["Month"], g["Actual CB Qty"]))

date_cols = ["Process Date", "ISA Date", "Wholesaler Invoice Date", "Received Date",
             "Wholesaler Debit Memo", " Wholesaler DM Date"]
date_cols = [c for c in date_cols if c in sub.columns]

months = [f"2025-{m:02d}" for m in range(3, 13)]
print(f"{'month':<9}{'GOLDEN':>10}", end="")
for c in date_cols:
    print(f"{c[:13]:>15}", end="")
print()
for ym in months:
    print(f"{ym:<9}{gold.get(ym, 0):>10,.0f}", end="")
    for c in date_cols:
        s = sub.copy()
        s["ym"] = pd.to_datetime(s[c], errors="coerce").dt.strftime("%Y-%m")
        q = s[s["ym"] == ym]["Chargeback Quantity"].sum()
        print(f"{q:>15,.0f}", end="")
    print()
