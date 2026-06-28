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
