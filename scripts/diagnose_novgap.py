"""Phase 1: is November under-covered? Check per-file + daily process-date counts."""
import os, sys, warnings
import pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/janish/Desktop/piramal-dashboard")
from utils.mappings import ndc_to_product

DL = os.path.expanduser("~/Downloads")
FILES = {
    "JanOct": os.path.join(DL, "Chargeback Detail V2.5 0101 to 3110.xlsx"),
    "NovDec": os.path.join(DL, "Chargeback_Detail_V2.5_20251101_20251231.xlsx"),
}


def _read(path):
    raw = pd.read_excel(path, header=None, nrows=8)
    hdr = 0
    for i in range(len(raw)):
        if any(m in [str(x) for x in raw.iloc[i].tolist()] for m in ["Process Date"]):
            hdr = i; break
    return pd.read_excel(path, header=hdr)


for tag, path in FILES.items():
    df = _read(path)
    df["pd"] = pd.to_datetime(df["Process Date"], errors="coerce")
    print(f"\n=== {tag}: rows={len(df):,}  process-date range {df['pd'].min()} -> {df['pd'].max()}")
    # all-product monthly totals in this file
    mt = df.groupby(df["pd"].dt.strftime("%Y-%m")).agg(
        rows=("Chargeback Quantity", "size"),
        qty=("Chargeback Quantity", "sum")).reset_index()
    print(mt.to_string(index=False))

# Daily November coverage (all products), combined
nd = _read(FILES["NovDec"])
nd["pd"] = pd.to_datetime(nd["Process Date"], errors="coerce")
nov = nd[(nd["pd"] >= "2025-11-01") & (nd["pd"] < "2025-12-01")]
print("\n=== November daily process-date coverage (NovDec file, all products) ===")
daily = nov.groupby(nov["pd"].dt.day).agg(rows=("Chargeback Quantity", "size")).reset_index()
print("days present:", sorted(nov["pd"].dt.day.unique()))
print("total Nov rows:", len(nov))
