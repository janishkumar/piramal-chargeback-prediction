"""Turn model outputs into formatted Dash sections for each tab."""
import numpy as np
import pandas as pd
from dash import dcc, html

from components.charts import accuracy_bar_line, error_histogram
from components.kpi_cards import kpi_row
from components.tables import data_table
from models.excel_model import compute_accrual
from models.ml_model import process_v7_results
from utils.format import fmt_dollar, fmt_pct, kpi_color, status_band


def empty_state(msg):
    return html.Div(msg, className="empty-state")


def _card(title, *children, note=None):
    kids = [html.H3(title)]
    if note:
        kids.append(html.Div(note, className="section-note"))
    kids.extend(children)
    return html.Div(className="card-panel", children=kids)


def _between(df, col, start, end):
    if start:
        df = df[df[col] >= start]
    if end:
        df = df[df[col] <= end]
    return df


# ============================ EXCEL TAB ============================

def excel_products(gross, cb):
    from utils.mappings import ndc_to_product
    prods = set()
    for df, c in [(gross, "NDC Number"), (cb, "NDC Number")]:
        if c in df.columns:
            prods |= set(df[c].map(ndc_to_product).unique())
    prods.discard("UNMAPPED")
    return sorted(prods)


def default_cutoff(months, lag=2):
    """Latest fully-mature CB month: chargebacks keep arriving for ~`lag` months,
    so months within `lag` of the most recent data are still 'partial'."""
    if not months:
        return None
    return str(pd.Period(max(months), freq="M") - lag)


def excel_body(gross, cb, product, start, end, complete_through=None):
    if gross.empty or cb.empty:
        return empty_state("Upload Gross Sales + CB Detail files to see results.")
    res = compute_accrual(gross, cb, product)
    if res.empty:
        return empty_state(f"No data for {product}.")
    res = _between(res, "year_month", start, end)
    if res.empty:
        return empty_state("No months in the selected range.")

    all_months = sorted(res["year_month"].tolist())
    cutoff = complete_through or default_cutoff(all_months)
    res["mature"] = res["year_month"] <= cutoff if cutoff else True
    mature = res[res["mature"]]
    n_partial = int((~res["mature"]).sum())

    # KPIs over MATURE *and* predictable months only: partial months have
    # incomplete actuals, and pre-prediction months (no accrual) would unbalance
    # the gap by adding actuals with no matching prediction.
    scored = mature[mature["accrual_pred"].notna()]
    total_accrual = scored["accrual_pred"].sum(skipna=True)
    total_actual = scored["actual_cb_amt"].sum(skipna=True)
    gap = total_accrual - total_actual
    gap_pct = gap / total_accrual if total_accrual else np.nan
    months_label = f"{len(scored)} mature" + (f" (+{n_partial} partial)" if n_partial else "")

    kpis = kpi_row([
        {"label": "Total Accrual (Predicted)", "value": fmt_dollar(total_accrual)},
        {"label": "Total Actual CB $", "value": fmt_dollar(total_actual), "color": "green"},
        {"label": "YTD Gap", "value": fmt_dollar(gap)},
        {"label": "YTD Gap %", "value": fmt_pct(gap_pct), "color": kpi_color(gap_pct)},
        {"label": "Active Months", "value": months_label},
    ])

    # Accrual table -- golden column names/order. Partial months: blank the gap
    # columns (misleading without complete actuals) and flag maturity.
    def _gap_cell(row, col, fmt):
        return fmt(row[col]) if row["mature"] else "— partial"

    disp = pd.DataFrame({
        "Month": res["year_month"],
        "Maturity": res["mature"].map(lambda m: "✓" if m else "⚠ partial"),
        "Primary Sales Qty": res["sales_qty"].map(lambda v: f"{v:,.0f}"),
        "Est CB Qty %": res["est_cb_pct"].map(fmt_pct),
        "Est CB Qty": res["est_cb_qty"].map(lambda v: f"{v:,.0f}" if pd.notna(v) else "-"),
        "Avg CB Per Unit": res["avg_cb_per_unit"].map(fmt_dollar),
        "Accrual": res["accrual_pred"].map(fmt_dollar),
        "Actual CB Qty": res["actual_cb_qty"].map(lambda v: f"{v:,.0f}"),
        "Actual CB Qty%": res["actual_cb_pct"].map(fmt_pct),
        "Actual CB / Unit": res["actual_cb_per_unit"].map(fmt_dollar),
        "Actual CB $": [_gap_cell(r, "actual_cb_amt", fmt_dollar) for _, r in res.iterrows()],
        "YTD GAP": [_gap_cell(r, "ytd_gap", fmt_dollar) for _, r in res.iterrows()],
        "YTD Gap %": [_gap_cell(r, "ytd_gap_pct", fmt_pct) for _, r in res.iterrows()],
    })
    grey_partial = [{
        "if": {"filter_query": '{Maturity} = "⚠ partial"'},
        "color": "#8b8fa3", "fontStyle": "italic",
    }]

    note = (f"Accrual Model (uses current-month data). YTD Gap is cumulative. "
            f"Chargebacks mature over ~2 months, so months after {cutoff} are "
            f"marked partial and excluded from the KPIs above.")

    chart = dcc.Graph(figure=accuracy_bar_line(
        mature.assign(err=mature["ytd_gap_pct"]),
        "accrual_pred", "actual_cb_amt", "err"))

    return html.Div([
        kpis,
        _card("Accrual Calculation",
              data_table(disp, "excel-accrual", extra_conditional=grey_partial),
              note=note),
        _card("Monthly Accuracy (mature months)", chart),
    ])


# ============================ ML TAB ==============================

def ml_body(v7, cb, view, product, start, end):
    if v7.empty:
        return empty_state("Upload v7_results.csv to see ML model results.")
    res = process_v7_results(v7, cb_detail_df=(None if cb.empty else cb))
    mp = _between(res["monthly_portfolio"], "month", start, end)

    total_pred = res["product_summary"]["total_v7"].sum()
    total_actual = res["product_summary"]["total_actual"].sum()
    err = (total_pred - total_actual) / total_actual if total_actual else np.nan
    pairs = res["pair_detail"]
    within10 = (pairs["error_pct"].abs() <= 0.10).mean()
    within20 = (pairs["error_pct"].abs() <= 0.20).mean()

    kpis = kpi_row([
        {"label": "Total Predicted CB", "value": fmt_dollar(total_pred), "color": "purple"},
        {"label": "Total Actual CB", "value": fmt_dollar(total_actual), "color": "green"},
        {"label": "Portfolio Error %", "value": fmt_pct(err), "color": kpi_color(err)},
        {"label": "Pairs within +/-10%", "value": f"{within10*100:.0f}%"},
        {"label": "Pairs within +/-20%", "value": f"{within20*100:.0f}%"},
    ])

    sections = [kpis, _card(
        "ML Forward Prediction (prior data only)",
        dcc.Graph(figure=accuracy_bar_line(mp, "total_v7", "total_actual", "error_pct", x_col="month")))]

    if view == "product":
        ps = res["product_summary"].sort_values("total_actual", ascending=False)
        disp = pd.DataFrame({
            "Product Group": ps["product_group"],
            "Total Actual ($)": ps["total_actual"].map(fmt_dollar),
            "Total V7 ($)": ps["total_v7"].map(fmt_dollar),
            "V7 Error %": ps["v7_error_pct"].map(fmt_pct),
            "Total EWM ($)": ps["total_ewm"].map(fmt_dollar),
            "EWM Error %": ps["ewm_error_pct"].map(fmt_pct),
            "V7 Win % (pairs)": ps["v7_win_pct"].map(fmt_pct),
            "V7 Better?": ps["v7_better"].map(lambda b: "Yes" if b else "No"),
        })
        sections.append(_card("Monthly Performance by Product",
                              data_table(disp, "ml-product")))
        sections.append(_card("Error Distribution",
                              dcc.Graph(figure=error_histogram(pairs["error_pct"]))))
    else:
        pd_view = pairs
        if product and product != "All":
            pd_view = pd_view[pd_view["product_group"] == product]
        disp = pd.DataFrame({
            "Agreement": pd_view["Agreement_norm"],
            "SKU": pd_view["SKU_norm"],
            "Product Group": pd_view["product_group"],
            "Wholesaler": pd_view["wholesaler"],
            "Months": pd_view["months"],
            "Avg Monthly ($)": pd_view["avg_monthly"].map(fmt_dollar),
            "Total Actual ($)": pd_view["total_actual"].map(fmt_dollar),
            "Total V7 ($)": pd_view["total_v7"].map(fmt_dollar),
            "Error %": pd_view["error_pct"].map(fmt_pct),
            "status": pd_view["status"],
        })
        sections.append(_card("Pair Detail",
                              data_table(disp, "ml-pair", page_size=50,
                                         searchable=True, status_colors=True)))

    # Business tier breakdown (always visible)
    tb = res["tier_breakdown"]
    tier_disp = pd.DataFrame({
        "Tier": tb["tier"],
        "Pairs": tb["pairs"],
        "Total CB ($)": tb["total_cb"].map(fmt_dollar),
        "% of CB": tb["pct_of_cb"].map(fmt_pct),
        "<10% Err": tb["within10"].map(fmt_pct),
        "<15% Err": tb["within15"].map(fmt_pct),
        "<20% Err": tb["within20"].map(fmt_pct),
        ">30% Err": tb["over30"].map(fmt_pct),
        "Avg V7 Err": tb["avg_v7_err"].map(fmt_pct),
    })
    sections.append(_card("Business Tier Breakdown", data_table(tier_disp, "ml-tier")))

    return html.Div(sections)
