from dash import html


def header():
    return html.Div(
        className="app-header",
        children=[
            html.Span("Piramal", className="brand"),
            html.Span("Chargeback Prediction Dashboard", className="title"),
            html.Span(className="spacer"),
            html.Span("ROI by Practus", className="kpi-label"),
        ],
    )
