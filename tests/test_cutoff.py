from components.render import default_cutoff


def test_default_cutoff_lags_two_months():
    months = ["2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08",
              "2025-09", "2025-10", "2025-11", "2025-12"]
    # data through Dec -> mature through Oct (Nov, Dec are partial)
    assert default_cutoff(months) == "2025-10"


def test_default_cutoff_year_boundary():
    assert default_cutoff(["2025-12", "2026-01"]) == "2025-11"


def test_default_cutoff_empty():
    assert default_cutoff([]) is None
