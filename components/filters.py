from dash import dcc, html

DD_STYLE = {"minWidth": "200px"}


def product_dropdown(dd_id, options, default=None):
    opts = [{"label": o, "value": o} for o in options]
    return html.Div(
        [
            html.Label("Product Group"),
            dcc.Dropdown(id=dd_id, options=opts, value=default, clearable=False,
                         style=DD_STYLE, className="dark-dd"),
        ]
    )


def month_range(start_id, end_id, months):
    opts = [{"label": m, "value": m} for m in months]
    first = months[0] if months else None
    last = months[-1] if months else None
    return html.Div(
        className="filter-bar",
        children=[
            html.Div([html.Label("Start Month"),
                      dcc.Dropdown(id=start_id, options=opts, value=first,
                                   clearable=False, style=DD_STYLE)]),
            html.Div([html.Label("End Month"),
                      dcc.Dropdown(id=end_id, options=opts, value=last,
                                   clearable=False, style=DD_STYLE)]),
        ],
    )


def view_toggle(toggle_id):
    return html.Div(
        [
            html.Label("View"),
            dcc.RadioItems(
                id=toggle_id,
                options=[{"label": " Product Level", "value": "product"},
                         {"label": " Pair Level", "value": "pair"}],
                value="product",
                inline=True,
            ),
        ]
    )


def error_slider(slider_id):
    return html.Div(
        [
            html.Label("Max Error %"),
            dcc.Slider(id=slider_id, min=0, max=100, step=5, value=100,
                       marks={0: "0", 20: "20", 50: "50", 100: "100"}),
        ],
        style={"minWidth": "260px"},
    )
