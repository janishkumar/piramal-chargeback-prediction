from dash import html


def kpi_card(label, value, color=None, delta=None, delta_color=None):
    classes = "kpi-card" + (f" {color}" if color else "")
    children = [
        html.Div(label, className="kpi-label"),
        html.Div(value, className="kpi-value"),
    ]
    if delta is not None:
        dc = f"kpi-delta {delta_color}" if delta_color else "kpi-delta"
        children.append(html.Div(delta, className=dc))
    return html.Div(className=classes, children=children)


def kpi_row(cards):
    """cards: list of dicts with keys label, value, color, delta, delta_color."""
    return html.Div(
        className="kpi-row",
        children=[kpi_card(**c) for c in cards],
    )
