from dash import dash_table

DARK_STYLE = dict(
    style_header={
        "backgroundColor": "#eef1f7",
        "color": "#1b1f2a",
        "fontWeight": "700",
        "border": "1px solid #dde2ec",
    },
    style_cell={
        "backgroundColor": "#ffffff",
        "color": "#1b1f2a",
        "border": "1px solid #dde2ec",
        "fontFamily": "Inter, sans-serif",
        "fontSize": "13px",
        "padding": "8px 12px",
        "textAlign": "right",
    },
    style_data={"backgroundColor": "#ffffff"},
)

# Color status cells GOOD/OK/BAD
STATUS_CONDITIONAL = [
    {"if": {"filter_query": '{status} = "GOOD"', "column_id": "status"},
     "color": "#2ecc71", "fontWeight": "700"},
    {"if": {"filter_query": '{status} = "OK"', "column_id": "status"},
     "color": "#f1c40f", "fontWeight": "700"},
    {"if": {"filter_query": '{status} = "BAD"', "column_id": "status"},
     "color": "#e74c3c", "fontWeight": "700"},
]


def data_table(df, table_id, page_size=None, searchable=False, status_colors=False,
               extra_conditional=None):
    fmt = []
    if status_colors:
        fmt = list(STATUS_CONDITIONAL)
    if extra_conditional:
        fmt = fmt + list(extra_conditional)
    kwargs = dict(
        id=table_id,
        columns=[{"name": str(c), "id": str(c)} for c in df.columns],
        data=df.to_dict("records"),
        sort_action="native",
        filter_action="native" if searchable else "none",
        style_data_conditional=fmt,
        style_as_list_view=False,
        # Wide tables scroll horizontally inside their card instead of
        # overflowing the border.
        style_table={"overflowX": "auto", "maxWidth": "100%"},
        **DARK_STYLE,
    )
    if page_size:
        kwargs["page_action"] = "native"
        kwargs["page_size"] = page_size
    return dash_table.DataTable(**kwargs)
