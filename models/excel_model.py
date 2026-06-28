"""Excel accrual model (replicates 'CB Forecast Model (3)').

Per product group, per month:
    Est_CB_Pct      = (CB_qty[i-1] + CB_qty[i]) / (Sales_qty[i-2] + Sales_qty[i-1])
    Est_CB_Qty      = Sales_Qty[i] * Est_CB_Pct
    Avg_CB_Per_Unit = SUMPRODUCT(vol_share[i], cpu[i]) * (1 + adj_factor[i])
    Accrual         = Est_CB_Qty * Avg_CB_Per_Unit

YTD GAP and YTD Gap % are CUMULATIVE (running sums), matching
excel_model_output.xlsx exactly.
"""
import numpy as np
import pandas as pd

from utils.mappings import WHOLESALER_GROUPS, classify_wholesaler, ndc_to_product


def _filter_product(df, date_col, product_group):
    d = df.copy()
    d["prod"] = d["NDC Number"].map(ndc_to_product)
    d = d[d["prod"] == product_group].copy()
    d["year_month"] = pd.to_datetime(d[date_col], errors="coerce").dt.strftime("%Y-%m")
    return d.dropna(subset=["year_month"])


def _prep_cb(cb_df, product_group, top_n=None):
    """Product CB rows tagged with wholesaler group, optionally restricted to
    the top-N contracts by total chargeback volume (matches the Excel filter)."""
    c = _filter_product(cb_df, "Process Date", product_group)
    c["wh"] = c["Wholesaler Name"].map(classify_wholesaler)
    if top_n and "Contract Number" in c.columns and not c.empty:
        rank = c.groupby("Contract Number")["Chargeback Quantity"].sum().sort_values(
            ascending=False)
        keep = set(rank.head(int(top_n)).index)
        c = c[c["Contract Number"].isin(keep)].copy()
    return c


def wholesaler_breakdown(cb_df, product_group, top_n=None):
    """Return (volume_share_df, cb_per_unit_df) per month per wholesaler group.

    volume_share: each group's share of monthly CB qty (fractions, + Total=1.0).
    cb_per_unit: each group's CB amount / CB qty in $ (+ Grand Total = weighted).
    """
    c = _prep_cb(cb_df, product_group, top_n)
    if c.empty:
        return pd.DataFrame(), pd.DataFrame()
    grp = (
        c.groupby(["year_month", "wh"])
        .agg(q=("Chargeback Quantity", "sum"), a=("Chargeback Amount", "sum"))
        .reset_index()
    )
    vol_rows, cpu_rows = [], []
    for m in sorted(c["year_month"].unique()):
        sub = grp[grp["year_month"] == m]
        qmap = dict(zip(sub["wh"], sub["q"]))
        amap = dict(zip(sub["wh"], sub["a"]))
        tot_q, tot_a = sum(qmap.values()), sum(amap.values())
        vrow, crow = {"Month": m}, {"Month": m}
        for g in WHOLESALER_GROUPS:
            q, a = float(qmap.get(g, 0.0)), float(amap.get(g, 0.0))
            vrow[g] = (q / tot_q) if tot_q else np.nan
            crow[g] = (a / q) if q else np.nan
        vrow["Total"] = 1.0 if tot_q else np.nan
        crow["Grand Total"] = (tot_a / tot_q) if tot_q else np.nan
        vol_rows.append(vrow)
        cpu_rows.append(crow)
    return pd.DataFrame(vol_rows), pd.DataFrame(cpu_rows)


def compute_accrual(gross_df, cb_df, product_group, adj_factor=None, top_n=None):
    """Return the per-month accrual frame for one product group.

    adj_factor: optional dict {year_month: float} for the (1 + adj) term.
    top_n: optional, restrict CB to the top-N contracts by volume.
    """
    g = _filter_product(gross_df, "Shipped Date", product_group)
    c = _prep_cb(cb_df, product_group, top_n)

    sales = g.groupby("year_month")["Shipped Quantity"].sum()
    cbq = c.groupby("year_month")["Chargeback Quantity"].sum()
    cba = c.groupby("year_month")["Chargeback Amount"].sum()

    months = sorted(set(sales.index) | set(cbq.index))
    rows = []
    for i, m in enumerate(months):
        s = float(sales.get(m, 0.0))
        cq = float(cbq.get(m, 0.0))
        ca = float(cba.get(m, 0.0))

        if i < 2:
            est_pct = np.nan
        else:
            denom = float(sales.get(months[i - 2], 0)) + float(sales.get(months[i - 1], 0))
            numer = float(cbq.get(months[i - 1], 0)) + float(cbq.get(m, 0))
            est_pct = numer / denom if denom else np.nan

        mc = c[c["year_month"] == m]
        adj = 0.0 if adj_factor is None else float(adj_factor.get(m, 0.0))
        if len(mc):
            by_wh = mc.groupby("wh").agg(
                q=("Chargeback Quantity", "sum"), a=("Chargeback Amount", "sum")
            )
            total_q = by_wh["q"].sum()
            if total_q:
                share = by_wh["q"] / total_q
                cpu = by_wh["a"] / by_wh["q"].replace(0, np.nan)
                avg_cpu = float((share * cpu).sum()) * (1 + adj)
            else:
                avg_cpu = np.nan
        else:
            avg_cpu = np.nan

        est_qty = s * est_pct if est_pct == est_pct else np.nan
        accrual = est_qty * avg_cpu if (est_qty == est_qty and avg_cpu == avg_cpu) else np.nan

        rows.append(
            dict(
                year_month=m,
                sales_qty=s,
                est_cb_pct=est_pct,
                est_cb_qty=est_qty,
                avg_cb_per_unit=avg_cpu,
                accrual_pred=accrual,
                actual_cb_qty=cq,
                actual_cb_pct=(cq / s if s else np.nan),
                actual_cb_per_unit=(ca / cq if cq else np.nan),
                actual_cb_amt=ca,
            )
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    # YTD gap accumulates only over predictable months (those with an accrual).
    # Pre-prediction months (the first two, no Est CB%) have actuals but no
    # accrual; including them would corrupt the gap, as the Excel model omits
    # them entirely and starts cumulating at the first predictable month.
    pred = out["accrual_pred"].notna()
    cum_acc = out["accrual_pred"].where(pred, 0).cumsum()
    cum_act = out["actual_cb_amt"].where(pred, 0).cumsum()
    out["ytd_gap"] = (cum_acc - cum_act).where(pred)
    out["ytd_gap_pct"] = (out["ytd_gap"] / cum_acc.replace(0, np.nan)).where(pred)
    return out
