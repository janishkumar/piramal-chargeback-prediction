import os
import pathlib
import sys

import pytest

# Make project root importable
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

DL = pathlib.Path(os.path.expanduser("~/Downloads"))


def _req(name):
    p = DL / name
    if not p.exists():
        pytest.skip(f"sample file missing: {p}")
    return p


@pytest.fixture
def v7_csv():
    return _req("v7_results.csv")


@pytest.fixture
def golden_xlsx():
    return _req("excel_model_output.xlsx")


@pytest.fixture
def cb_xlsx():
    return _req("Chargeback_Detail_V2.5_20251101_20251231.xlsx")


@pytest.fixture
def gross_xlsx():
    return _req("Nov_Dec_Gross_Sales_For_Paste.xlsx")
