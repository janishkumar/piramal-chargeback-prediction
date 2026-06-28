"""Phase 1: compare our monthly CB qty/amount (by Process Date) vs golden Actual."""
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
cb["ym"] = pd.to_datetime(cb["Process Date"], errors="coerce").dt.strftime("%Y-%m")

prod = "SEVOFLURANE"
sub = cb[cb["prod"] == prod]
ours = sub.groupby("ym").agg(
    rows=("Chargeback Quantity", "size"),
    cb_qty=("Chargeback Quantity", "sum"),
    cb_amt=("Chargeback Amount", "sum"),
).reset_index()

g = pd.read_excel(GOLDEN, sheet_name=prod, header=2).dropna(subset=["Month"])
g["Month"] = g["Month"].astype(str)
m = ours.merge(g, left_on="ym", right_on="Month", how="right")

print(f"{prod}: our CB (by Process Date) vs golden Actual")
print(f"{'month':<9}{'rows':>7}{'cbqty_ours':>12}{'cbqty_gold':>12}{'qty_ratio':>11}"
      f"{'cbamt_ours':>14}{'cbamt_gold':>14}")
for _, r in m.iterrows():
    ro = r["cb_qty"] / r["Actual CB Qty"] if r.get("Actual CB Qty") else float("nan")
    print(f"{str(r['Month']):<9}{(r['rows'] or 0):>7.0f}{(r['cb_qty'] or 0):>12,.0f}"
          f"{r['Actual CB Qty']:>12,.0f}{ro:>11.3f}"
          f"{(r['cb_amt'] or 0):>14,.0f}{r['Actual CB $']:>14,.0f}")

print("\nAll CB process-date months present in our data:", sorted(cb['ym'].dropna().unique()))
