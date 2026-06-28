import pandas as pd
import pytest

from models.excel_model import compute_accrual


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
