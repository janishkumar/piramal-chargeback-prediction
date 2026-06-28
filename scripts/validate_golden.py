"""Validate Excel model output against the golden excel_model_output.xlsx.

Loads full-year Gross Sales + CB Detail (Jan-Oct from Azure/SharePoint + Nov-Dec),
runs compute_accrual per product, and compares Accrual / Est CB Qty / YTD GAP /
YTD Gap % against the golden per-product sheets for the Mar-Dec span.
"""
import os
import sys
import warnings

import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/janish/Desktop/piramal-dashboard")
from models.excel_model import compute_accrual  # noqa: E402

DL = os.path.expanduser("~/Downloads")
OD = os.path.join(DL, "OneDrive_1_6-28-2026")

GROSS = [
    os.path.join(OD, "Gross Sales V1.9 0101 3110.xlsx"),
    os.path.join(OD, "Gross_Sales_V1.9_20251101_20251231.xlsx"),
]
CB = [
    os.path.join(DL, "Chargeback Detail V2.5 0101 to 3110.xlsx"),
    os.path.join(DL, "Chargeback_Detail_V2.5_20251101_20251231.xlsx"),
]
GOLDEN = os.path.join(DL, "excel_model_output.xlsx")


def _read_detect(path, markers):
    """Read an xlsx, auto-detecting the header row by marker columns."""
    raw = pd.read_excel(path, header=None, nrows=8)
    hdr = 0
    for i in range(len(raw)):
        row = [str(x) for x in raw.iloc[i].tolist()]
        if any(m in row for m in markers):
            hdr = i
            break
    return pd.read_excel(path, header=hdr)


def load_concat(paths, markers):
    frames = [_read_detect(p, markers) for p in paths]
    return pd.concat(frames, ignore_index=True)


def golden_sheet(xls, sheet):
    g = pd.read_excel(xls, sheet_name=sheet, header=2)
    return g.dropna(subset=["Month"]).reset_index(drop=True)


def main():
    print("Loading Gross Sales ...")
    gross = load_concat(GROSS, ["Shipped Date", "Shipped Quantity"])
    print(f"  gross rows: {len(gross):,}")
    print("Loading CB Detail (51MB file, be patient) ...")
    cb = load_concat(CB, ["Process Date", "Chargeback Quantity"])
    print(f"  cb rows: {len(cb):,}")

    xls = pd.ExcelFile(GOLDEN)
    products = [s for s in xls.sheet_names if s != "Summary"]

    print(f"\n{'Product':<18}{'months':>7}{'Accrual MAPE':>14}{'YTDgap MAPE':>13}{'verdict':>10}")
    print("-" * 62)
    overall = []
    for prod in products:
        try:
            g = golden_sheet(xls, prod)
            out = compute_accrual(gross, cb, prod)
            m = out.merge(g, left_on="year_month", right_on="Month", how="inner")
            m = m[m["accrual_pred"].notna() & (m["Accrual"] != 0)]
            if not len(m):
                print(f"{prod:<18}{0:>7}{'no overlap':>14}")
                continue
            acc_mape = ((m["accrual_pred"] - m["Accrual"]).abs() / m["Accrual"].abs()).mean()
            # YTD gap compare where golden gap nonzero
            mg = m[m["YTD GAP"].abs() > 1]
            gap_mape = ((mg["ytd_gap"] - mg["YTD GAP"]).abs() / mg["YTD GAP"].abs()).mean() if len(mg) else float("nan")
            verdict = "MATCH" if acc_mape < 0.01 else ("CLOSE" if acc_mape < 0.05 else "DIFF")
            overall.append(acc_mape)
            print(f"{prod:<18}{len(m):>7}{acc_mape*100:>13.2f}%{gap_mape*100:>12.2f}%{verdict:>10}")
        except Exception as e:
            print(f"{prod:<18} ERROR: {e}")
    if overall:
        print("-" * 62)
        print(f"Mean Accrual MAPE across products: {sum(overall)/len(overall)*100:.3f}%")


if __name__ == "__main__":
    main()
