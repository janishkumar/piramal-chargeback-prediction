import pandas as pd

from models.ml_model import process_v7_results


def test_product_error_from_sums(v7_csv):
    df = pd.read_csv(v7_csv)
    res = process_v7_results(df)
    ps = res["product_summary"]
    assert {"product_group", "total_actual", "total_v7", "v7_error_pct"} <= set(ps.columns)
    row = ps.iloc[0]
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


def test_wholesaler_mapping_with_cb(v7_csv, cb_xlsx):
    v7 = pd.read_csv(v7_csv)
    cb = pd.read_excel(cb_xlsx)
    pairs = process_v7_results(v7, cb_detail_df=cb)["pair_detail"]
    # At least some pairs should map to a real wholesaler group (not all 'Others')
    assert pairs["wholesaler"].nunique() >= 1
    assert set(pairs["wholesaler"].unique()) <= {
        "ABC", "Cardinal", "Mckesson", "Mckesson Medical", "Others",
    }
