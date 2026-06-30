import pandas as pd
import pytest

from models.excel_model import compute_accrual, wholesaler_breakdown
from utils.mappings import WHOLESALER_GROUPS


def _golden(golden_xlsx, sheet):
    raw = pd.read_excel(golden_xlsx, sheet_name=sheet, header=2)
    return raw.dropna(subset=["Month"]).reset_index(drop=True)


def test_ytd_gap_is_cumulative(golden_xlsx):
    """Apr YTD GAP == cumulative(Accrual) - cumulative(Actual CB $) through Apr."""
    g = _golden(golden_xlsx, "SEVOFLURANE")
    cum_acc = g["Accrual"].iloc[:2].sum()
    cum_act = g["Actual CB $"].iloc[:2].sum()
    assert abs((cum_acc - cum_act) - g["YTD GAP"].iloc[1]) < 1.0


def test_ytd_gap_pct_is_cumulative(golden_xlsx):
    g = _golden(golden_xlsx, "SEVOFLURANE")
    cum_acc = g["Accrual"].iloc[:2].sum()
    cum_act = g["Actual CB $"].iloc[:2].sum()
    expected = (cum_acc - cum_act) / cum_acc
    assert abs(expected - g["YTD Gap %"].iloc[1]) < 1e-3


def test_compute_accrual_parity_overlap(gross_xlsx, cb_xlsx, golden_xlsx):
    """Parity on whatever months the sample gross/cb files overlap the golden."""
    g = _golden(golden_xlsx, "SEVOFLURANE")
    out = compute_accrual(
        pd.read_excel(gross_xlsx), pd.read_excel(cb_xlsx), "SEVOFLURANE"
    )
    if out.empty:
        pytest.skip("no SEVOFLURANE rows in sample gross/cb files")
    merged = out.merge(g, left_on="year_month", right_on="Month", how="inner")
    if len(merged) == 0:
        pytest.skip("sample gross/cb months do not overlap golden period")
    for _, r in merged.iterrows():
        if r["Accrual"] and r["accrual_pred"] == r["accrual_pred"]:
            assert abs(r["accrual_pred"] - r["Accrual"]) / max(r["Accrual"], 1) < 0.05


def test_wholesaler_breakdown_shape_and_shares(cb_xlsx, gross_xlsx):
    vol, cpu = wholesaler_breakdown(
        pd.read_excel(gross_xlsx), pd.read_excel(cb_xlsx), "SEVOFLURANE"
    )
    if vol.empty:
        pytest.skip("no SEVOFLURANE rows in sample")
    # both tables have a Month col + the five wholesaler groups
    for grp in WHOLESALER_GROUPS:
        assert grp in vol.columns and grp in cpu.columns
    assert "Total" in vol.columns and "Grand Total" in cpu.columns
    # volume shares across the five groups sum to ~1.0 each month
    for _, row in vol.iterrows():
        s = sum(row[g] for g in WHOLESALER_GROUPS if pd.notna(row[g]))
        assert abs(s - 1.0) < 1e-6


def test_top_n_contracts_reduces_or_equals_cb(cb_xlsx, gross_xlsx):
    gross, cb = pd.read_excel(gross_xlsx), pd.read_excel(cb_xlsx)
    full = compute_accrual(gross, cb, "SEVOFLURANE")
    top = compute_accrual(gross, cb, "SEVOFLURANE", top_n=15)
    if full.empty or top.empty:
        pytest.skip("no SEVOFLURANE rows in sample")
    # restricting to top-15 contracts can only keep or lower total actual CB
    assert top["actual_cb_amt"].sum() <= full["actual_cb_amt"].sum() + 1.0
