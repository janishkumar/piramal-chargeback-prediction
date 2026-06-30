import plotly.graph_objects as go

BLUE = "#4f8ff7"
GREEN = "#2ecc71"
YELLOW = "#f1c40f"
RED = "#e74c3c"
PURPLE = "#9b59b6"

LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    font=dict(family="Inter, sans-serif", color="#1b1f2a"),
    margin=dict(l=50, r=50, t=40, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)


def accuracy_bar_line(df, pred_col, actual_col, err_col, x_col="year_month"):
    """Grouped predicted/actual bars + error% line on secondary axis."""
    fig = go.Figure()
    fig.add_bar(x=df[x_col], y=df[pred_col], name="Predicted", marker_color=BLUE)
    fig.add_bar(x=df[x_col], y=df[actual_col], name="Actual", marker_color=GREEN)
    fig.add_trace(
        go.Scatter(
            x=df[x_col],
            y=df[err_col] * 100,
            name="Error %",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color=YELLOW, width=2),
        )
    )
    fig.update_layout(
        barmode="group",
        yaxis=dict(title="Amount ($)"),
        yaxis2=dict(title="Error %", overlaying="y", side="right", showgrid=False),
        **LAYOUT,
    )
    return fig


def error_histogram(errors):
    """Histogram of pair-level errors with 10/20/30% reference lines."""
    pct = (errors.dropna() * 100)
    fig = go.Figure()
    fig.add_histogram(x=pct, marker_color=PURPLE, nbinsx=40, name="Pairs")
    for thr, color in [(10, GREEN), (20, YELLOW), (30, RED)]:
        for sign in (1, -1):
            fig.add_vline(x=sign * thr, line_dash="dash", line_color=color, opacity=0.6)
    fig.update_layout(
        xaxis=dict(title="Error %", range=[-100, 100]),
        yaxis=dict(title="Pair count"),
        **LAYOUT,
    )
    return fig
