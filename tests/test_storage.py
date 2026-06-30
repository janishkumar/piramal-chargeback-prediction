import pandas as pd

from utils.storage import LocalStorage


def test_append_dedup_cb(tmp_path):
    st = LocalStorage(tmp_path)
    df = pd.DataFrame(
        {
            "Chargeback Number": [1, 1, 2],
            "Line Number": [1, 1, 1],
            "Chargeback Amount": [10, 10, 5],
        }
    )
    st.append_cb_detail(df)
    st.append_cb_detail(df)  # full overlap -> no growth
    out = st.load_cb_detail()
    assert len(out) == 2  # (1,1) and (2,1) deduped


def test_gross_keeps_distinct_lots_sharing_invoice_line(tmp_path):
    # Same Invoice/Line/Order but different Lot/Qty are DISTINCT shipments and
    # must all survive (regression: coarse-key dedup dropped real volume).
    st = LocalStorage(tmp_path)
    df = pd.DataFrame({
        "Invoice Number": [50165, 50165, 50165],
        "Line Number": [2, 2, 2],
        "Order Number": [145480, 145480, 145480],
        "Lot Code": ["A", "B", "C"],
        "Shipped Quantity": [1440, 720, 2160],
    })
    st.append_gross(df)
    out = st.load_gross()
    assert len(out) == 3
    assert out["Shipped Quantity"].sum() == 4320
    st.append_gross(df)  # re-upload identical file -> no growth
    assert len(st.load_gross()) == 3


def test_v7_replaces(tmp_path):
    st = LocalStorage(tmp_path)
    st.save_v7(pd.DataFrame({"a": [1, 2, 3]}))
    st.save_v7(pd.DataFrame({"a": [9]}))
    assert len(st.load_v7()) == 1


def test_session_roundtrip(tmp_path):
    st = LocalStorage(tmp_path)
    sid = st.create_session(label="Nov-Dec 2025", start="2025-11", end="2025-12")
    sessions = st.list_sessions()
    assert any(s["id"] == sid for s in sessions)
