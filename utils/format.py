"""Shared display formatters and threshold helpers.

Threshold schemes (unified per design spec ยง7.1):
  - KPI error coloring: green <=5%, yellow <=15%, red >15%
  - Status bands:       GOOD <=10%, OK <=20%, BAD >20%
"""


def fmt_dollar(v):
    try:
        return f"${round(float(v)):,}"
    except (TypeError, ValueError):
        return "-"


def fmt_pct(v, digits=1):
    try:
        return f"{float(v) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "-"


def kpi_color(err):
    a = abs(err)
    return "green" if a <= 0.05 else ("yellow" if a <= 0.15 else "red")


def status_band(err):
    a = abs(err)
    return "GOOD" if a <= 0.10 else ("OK" if a <= 0.20 else "BAD")
