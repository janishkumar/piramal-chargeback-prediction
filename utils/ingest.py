"""File-type detection and parsing for uploads.

Detect type from column headers (PRD ยง9.2):
  Shipped Quantity + NDC Number          -> gross_sales
  Chargeback Amount + Process Date       -> cb_detail
  pred_v7_final + Agreement_norm         -> v7_results
  Shipped Quantity + Invoice Number      -> sales_detail (optional)
"""
import base64
import io

import pandas as pd

REQUIRED = {
    "gross_sales": ["Shipped Date", "Shipped Quantity", "NDC Number"],
    "cb_detail": ["Process Date", "Chargeback Quantity", "Chargeback Amount",
                  "NDC Number", "Wholesaler Name"],
    "v7_results": ["Agreement_norm", "SKU_norm", "month", "pred_v7_final", "actual"],
}


def detect_file_type(columns):
    cols = set(columns)
    if {"pred_v7_final", "Agreement_norm"} <= cols:
        return "v7_results"
    if {"Chargeback Amount", "Process Date"} <= cols:
        return "cb_detail"
    if {"Shipped Quantity", "NDC Number"} <= cols and "Invoice Number" not in cols:
        return "gross_sales"
    if {"Shipped Quantity", "Invoice Number"} <= cols and "Chargeback Amount" not in cols:
        # gross sales sample also carries Invoice Number; treat as gross if it
        # has NDC + Shipped Date, else sales_detail
        if {"NDC Number", "Shipped Date"} <= cols:
            return "gross_sales"
        return "sales_detail"
    return "unknown"


def missing_columns(file_type, columns):
    req = REQUIRED.get(file_type, [])
    return [c for c in req if c not in set(columns)]


def parse_contents(contents, filename):
    """Decode a dcc.Upload payload into a DataFrame."""
    _, content_string = contents.split(",", 1)
    decoded = base64.b64decode(content_string)
    if filename.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(decoded))
    return pd.read_excel(io.BytesIO(decoded))


def detected_date_range(df, file_type):
    col = {"gross_sales": "Shipped Date", "cb_detail": "Process Date"}.get(file_type)
    if col and col in df.columns:
        d = pd.to_datetime(df[col], errors="coerce").dropna()
        if len(d):
            return d.min().strftime("%Y-%m"), d.max().strftime("%Y-%m")
    if file_type == "v7_results" and "month" in df.columns:
        m = df["month"].dropna().astype(str)
        if len(m):
            return m.min(), m.max()
    return None, None
