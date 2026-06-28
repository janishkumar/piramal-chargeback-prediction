import pandas as pd

from components import render
from utils.storage import LocalStorage


def test_app_imports():
    import app
    assert app.server is not None


def test_excel_body_renders(tmp_path, gross_xlsx, cb_xlsx):
    st = LocalStorage(tmp_path)
    st.append_gross(pd.read_excel(gross_xlsx))
    st.append_cb_detail(pd.read_excel(cb_xlsx))
    prods = render.excel_products(st.load_gross(), st.load_cb_detail())
    assert prods  # at least one product detected
    comp = render.excel_body(st.load_gross(), st.load_cb_detail(), prods[0], None, None)
    assert comp is not None


def test_ml_body_renders(tmp_path, v7_csv, cb_xlsx):
    st = LocalStorage(tmp_path)
    st.save_v7(pd.read_csv(v7_csv))
    st.append_cb_detail(pd.read_excel(cb_xlsx))
    for view in ("product", "pair"):
        comp = render.ml_body(st.load_v7(), st.load_cb_detail(), view, "All", None, None)
        assert comp is not None


def test_empty_states():
    empty = pd.DataFrame()
    assert render.excel_body(empty, empty, "SEVOFLURANE", None, None) is not None
    assert render.ml_body(empty, empty, "product", "All", None, None) is not None
