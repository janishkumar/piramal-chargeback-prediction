import pandas as pd

from utils.ingest import detect_file_type, detected_date_range, missing_columns


def test_detect_v7():
    assert detect_file_type(["Agreement_norm", "SKU_norm", "pred_v7_final", "actual"]) == "v7_results"


def test_detect_cb():
    assert detect_file_type(["Process Date", "Chargeback Amount", "NDC Number"]) == "cb_detail"


def test_detect_gross():
    assert detect_file_type(["Shipped Date", "Shipped Quantity", "NDC Number"]) == "gross_sales"


def test_detect_unknown():
    assert detect_file_type(["foo", "bar"]) == "unknown"


def test_missing_columns():
    assert missing_columns("cb_detail", ["Process Date"]) == [
        "Chargeback Quantity", "Chargeback Amount", "NDC Number", "Wholesaler Name"
    ]


def test_date_range_v7():
    df = pd.DataFrame({"month": ["2025-09", "2025-12", "2025-10"]})
    assert detected_date_range(df, "v7_results") == ("2025-09", "2025-12")


def test_detect_real_files(cb_xlsx, gross_xlsx, v7_csv):
    import pandas as pd
    assert detect_file_type(pd.read_excel(cb_xlsx, nrows=1).columns) == "cb_detail"
    assert detect_file_type(pd.read_excel(gross_xlsx, nrows=1).columns) == "gross_sales"
    assert detect_file_type(pd.read_csv(v7_csv, nrows=1).columns) == "v7_results"
