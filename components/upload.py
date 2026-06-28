from dash import dcc, html


def upload_panel():
    return html.Div(
        className="card-panel",
        children=[
            html.H3("Upload New Data"),
            html.Div(
                "Drop Gross Sales, CB Detail, or v7_results files here. "
                "Type is auto-detected from columns.",
                className="section-note",
            ),
            dcc.Upload(
                id="uploader",
                multiple=True,
                children=html.Div(["Drag & drop or ", html.B("browse"), " files"]),
                className="upload-area",
                accept=".xlsx,.csv",
            ),
            dcc.Loading(html.Div(id="upload-feedback")),
            html.Div(id="upload-history"),
        ],
    )
