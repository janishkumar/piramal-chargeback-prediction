"""V7 ML results processing for dashboard display.

Reads a v7_results dataframe and produces pair / product / monthly / tier
frames. The ML tab is a pure viewer: no training or prediction happens here.

Product-level error is computed from summed predictions and actuals (not the
average of pair-level errors).
"""
import numpy as np
import pandas as pd

from utils.mappings import classify_wholesaler, ndc_to_product

# (low, high, label) -- avg monthly CB per pair
TIERS = [
    (100_000, np.inf, ">$100K"),
    (50_000, 100_000, "$50K-$100K"),
    (25_000, 50_000, "$25K-$50K"),
    (10_000, 25_000, "$10K-$25K"),
    (5_000, 10_000, "$5K-$10K"),
    (1_000, 5_000, "$1K-$5K"),
    (-np.inf, 1_000, "<$1K"),
]


def _status(err):
    if pd.isna(err):
        return "BAD"
    a = abs(err)
    return "GOOD" if a <= 0.10 else ("OK" if a <= 0.20 else "BAD")


def _err(pred, act):
    return (pred - act) / act if act else np.nan


def _as_id(x):
    return str(int(x)) if pd.notna(x) else x


def _tier_of(v):
    for lo, hi, name in TIERS:
        if lo <= v < hi:
            return name
    return "<$1K"


def process_v7_results(v7_df, cb_detail_df=None):
    df = v7_df.copy()
    df["SKU_norm"] = df["SKU_norm"].apply(_as_id)
    df["Agreement_norm"] = df["Agreement_norm"].apply(_as_id)
    df["product_group"] = df["SKU_norm"].map(ndc_to_product)

    # Agreement (== Contract Number) -> dominant wholesaler
    wh_map = {}
    if cb_detail_df is not None and "Contract Number" in cb_detail_df.columns:
        cb = cb_detail_df.copy()
        cb["wh"] = cb["Wholesaler Name"].map(classify_wholesaler)
        cb["Contract Number"] = cb["Contract Number"].apply(_as_id)
        wh_map = (
            cb.dropna(subset=["Contract Number"])
            .groupby("Contract Number")["wh"]
            .agg(lambda s: s.mode().iloc[0] if len(s.mode()) else "Others")
            .to_dict()
        )

    # ---- pair detail (aggregate across months per Agreement x SKU) ----
    pg = (
        df.groupby(["Agreement_norm", "SKU_norm", "product_group"])
        .agg(
            months=("month", "nunique"),
            total_actual=("actual", "sum"),
            total_v7=("pred_v7_final", "sum"),
            total_ewm=("pred_ewm", "sum"),
        )
        .reset_index()
    )
    pg["avg_monthly"] = pg["total_actual"] / pg["months"].replace(0, np.nan)
    pg["error_pct"] = pg.apply(lambda r: _err(r["total_v7"], r["total_actual"]), axis=1)
    pg["ewm_error_pct"] = pg.apply(lambda r: _err(r["total_ewm"], r["total_actual"]), axis=1)
    # V7 wins a pair when its absolute error is strictly smaller than EWM's.
    pg["v7_wins"] = pg["error_pct"].abs() < pg["ewm_error_pct"].abs()
    pg["status"] = pg["error_pct"].apply(_status)
    pg["wholesaler"] = pg["Agreement_norm"].map(wh_map).fillna("Others")
    pg["tier"] = pg["avg_monthly"].fillna(0).apply(_tier_of)

    # ---- product summary (error from sums) ----
    ps = (
        df.groupby("product_group")
        .agg(
            total_actual=("actual", "sum"),
            total_v7=("pred_v7_final", "sum"),
            total_ewm=("pred_ewm", "sum"),
        )
        .reset_index()
    )
    ps["v7_error_pct"] = (ps["total_v7"] - ps["total_actual"]) / ps["total_actual"].replace(0, np.nan)
    ps["ewm_error_pct"] = (ps["total_ewm"] - ps["total_actual"]) / ps["total_actual"].replace(0, np.nan)

    # CB-dollar-weighted share of each product's pairs where V7 beats EWM.
    # This reflects V7's pair-level edge; aggregate totals let errors cancel.
    win = pg.assign(_w=pg["v7_wins"] * pg["total_actual"].abs())
    win = (
        win.groupby("product_group")
        .agg(_win_cb=("_w", "sum"), _tot_cb=("total_actual", lambda s: s.abs().sum()))
        .reset_index()
    )
    win["v7_win_pct"] = win["_win_cb"] / win["_tot_cb"].replace(0, np.nan)
    ps = ps.merge(win[["product_group", "v7_win_pct"]], on="product_group", how="left")
    # "V7 Better?" now means V7 wins the majority of the product's CB dollars.
    ps["v7_better"] = ps["v7_win_pct"] >= 0.5

    # ---- monthly portfolio ----
    mp = (
        df.groupby("month")
        .agg(total_actual=("actual", "sum"), total_v7=("pred_v7_final", "sum"))
        .reset_index()
    )
    mp["error_pct"] = (mp["total_v7"] - mp["total_actual"]) / mp["total_actual"].replace(0, np.nan)

    # ---- business tier breakdown ----
    tb = (
        pg.groupby("tier")
        .agg(
            pairs=("SKU_norm", "count"),
            total_cb=("total_actual", "sum"),
            within10=("error_pct", lambda s: (s.abs() <= 0.10).mean()),
            within15=("error_pct", lambda s: (s.abs() <= 0.15).mean()),
            within20=("error_pct", lambda s: (s.abs() <= 0.20).mean()),
            over30=("error_pct", lambda s: (s.abs() > 0.30).mean()),
            avg_v7_err=("error_pct", lambda s: s.abs().mean()),
        )
        .reset_index()
    )
    total_cb_all = tb["total_cb"].sum()
    tb["pct_of_cb"] = tb["total_cb"] / total_cb_all if total_cb_all else np.nan

    return {
        "pair_detail": pg,
        "product_summary": ps,
        "monthly_portfolio": mp,
        "tier_breakdown": tb,
    }
