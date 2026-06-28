"""Piramal CB Prediction Dashboard — Dash app entrypoint."""
import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

from components import render
from components.filters import (error_slider, month_range, product_dropdown,
                                view_toggle)
from components.header import header
from components.upload import upload_panel
from utils.ingest import (detect_file_type, detected_date_range, missing_columns,
                          parse_contents)
from utils.mappings import ndc_to_product
from utils.storage import LocalStorage

DATA_ROOT = os.environ.get("DATA_ROOT", os.path.join(os.path.dirname(__file__), "data"))
store = LocalStorage(DATA_ROOT)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
                suppress_callback_exceptions=True, title="Piramal CB Dashboard")
server = app.server

app.layout = html.Div([
    header(),
    dcc.Store(id="refresh", data=0),
    html.Div(className="content", children=[
        upload_panel(),
        dcc.Tabs(id="tabs", value="excel", className="tab-container", children=[
            dcc.Tab(label="Excel Model", value="excel",
                    className="custom-tab", selected_className="custom-tab--selected"),
            dcc.Tab(label="ML Model", value="ml",
                    className="custom-tab", selected_className="custom-tab--selected"),
        ]),
        html.Div(id="tab-content"),
    ]),
])


# ---------------- Upload ----------------
@app.callback(
    Output("upload-feedback", "children"),
    Output("refresh", "data"),
    Input("uploader", "contents"),
    State("uploader", "filename"),
    State("refresh", "data"),
    prevent_initial_call=True,
)
def handle_upload(contents_list, names, refresh):
    if not contents_list:
        return dash.no_update, dash.no_update
    msgs = []
    starts, ends = [], []
    for contents, name in zip(contents_list, names):
        try:
            df = parse_contents(contents, name)
        except Exception as e:  # noqa: BLE001
            msgs.append(html.Div(f"❌ {name}: could not read ({e})", style={"color": "#e74c3c"}))
            continue
        ftype = detect_file_type(df.columns)
        miss = missing_columns(ftype, df.columns)
        if ftype == "unknown":
            msgs.append(html.Div(f"⚠️ {name}: unrecognized file type", style={"color": "#f1c40f"}))
            continue
        if miss:
            msgs.append(html.Div(f"❌ {name} ({ftype}): missing {', '.join(miss)}",
                                 style={"color": "#e74c3c"}))
            continue
        if ftype == "gross_sales":
            store.append_gross(df)
        elif ftype == "cb_detail":
            store.append_cb_detail(df)
        elif ftype == "v7_results":
            store.save_v7(df)
        s, e = detected_date_range(df, ftype)
        if s:
            starts.append(s); ends.append(e)
        msgs.append(html.Div(
            [html.Span(ftype, className="file-badge"),
             f" {name} — {len(df):,} rows" + (f", {s}→{e}" if s else "")],
            style={"color": "#2ecc71", "margin": "4px 0"}))
    if starts:
        store.create_session(label=f"{min(starts)}→{max(ends)}",
                             start=min(starts), end=max(ends))
    return html.Div(msgs), (refresh or 0) + 1


# ---------------- Tab shell ----------------
@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("refresh", "data"),
)
def render_tab(tab, _refresh):
    gross, cb, v7 = store.load_gross(), store.load_cb_detail(), store.load_v7()
    if tab == "excel":
        prods = render.excel_products(gross, cb)
        default = "SEVOFLURANE" if "SEVOFLURANE" in prods else (prods[0] if prods else None)
        months = sorted(set(
            (compute_months(gross, "Shipped Date") | compute_months(cb, "Process Date"))))
        return html.Div([
            html.Div(className="filter-bar", children=[
                product_dropdown("excel-product", prods, default),
                month_range("excel-start", "excel-end", months),
            ]),
            html.Div(id="excel-body"),
        ])
    else:
        v7_months = sorted(v7["month"].astype(str).unique()) if not v7.empty else []
        prods = ["All"] + (sorted(set(v7["SKU_norm"].map(ndc_to_product)) - {"UNMAPPED"})
                           if not v7.empty else [])
        return html.Div([
            html.Div(className="filter-bar", children=[
                view_toggle("ml-view"),
                product_dropdown("ml-product", prods, "All"),
                month_range("ml-start", "ml-end", v7_months),
                error_slider("ml-error"),
            ]),
            html.Div(id="ml-body"),
        ])


def compute_months(df, col):
    import pandas as pd
    if df.empty or col not in df.columns:
        return set()
    return set(pd.to_datetime(df[col], errors="coerce").dropna().dt.strftime("%Y-%m"))


# ---------------- Excel body ----------------
@app.callback(
    Output("excel-body", "children"),
    Input("excel-product", "value"),
    Input("excel-start", "value"),
    Input("excel-end", "value"),
)
def update_excel(product, start, end):
    if not product:
        return render.empty_state("Upload Gross Sales + CB Detail files to see results.")
    return render.excel_body(store.load_gross(), store.load_cb_detail(), product, start, end)


# ---------------- ML body ----------------
@app.callback(
    Output("ml-body", "children"),
    Input("ml-view", "value"),
    Input("ml-product", "value"),
    Input("ml-start", "value"),
    Input("ml-end", "value"),
)
def update_ml(view, product, start, end):
    return render.ml_body(store.load_v7(), store.load_cb_detail(), view, product, start, end)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
