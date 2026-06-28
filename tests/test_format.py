from utils.format import fmt_dollar, fmt_pct, kpi_color, status_band


def test_fmt_dollar():
    assert fmt_dollar(1234567) == "$1,234,567"
    assert fmt_dollar(None) == "-"


def test_fmt_pct():
    assert fmt_pct(0.2594) == "25.9%"
    assert fmt_pct(None) == "-"


def test_kpi_color():
    assert kpi_color(0.04) == "green"
    assert kpi_color(0.12) == "yellow"
    assert kpi_color(0.20) == "red"


def test_status_band():
    assert status_band(0.05) == "GOOD"
    assert status_band(0.15) == "OK"
    assert status_band(0.25) == "BAD"
