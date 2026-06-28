"""Pluggable storage. Local backend (SQLite metadata + parquet facts) for dev.

Raw transaction facts append with dedup on natural keys so overlapping monthly
uploads don't double-count. v7_results is a full backtest, so it replaces.

A future `azure` backend (Blob + Postgres) implements the same interface;
select via STORAGE_BACKEND env var in app wiring.
"""
import pathlib
import sqlite3
import uuid

import pandas as pd

CB_KEYS = ["Chargeback Number", "Line Number"]
GROSS_KEYS = ["Invoice Number", "Line Number", "Order Number"]


class LocalStorage:
    def __init__(self, root):
        self.root = pathlib.Path(root)
        (self.root / "facts").mkdir(parents=True, exist_ok=True)
        self.db = self.root / "db.sqlite"
        self._init_db()

    def _init_db(self):
        con = sqlite3.connect(self.db)
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions(
              id TEXT PRIMARY KEY,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              label TEXT,
              date_range_start TEXT,
              date_range_end TEXT,
              status TEXT DEFAULT 'complete');
            CREATE TABLE IF NOT EXISTS uploaded_files(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT,
              filename TEXT,
              file_type TEXT,
              row_count INTEGER,
              uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            """
        )
        con.commit()
        con.close()

    # ---- facts ----
    def _fact_path(self, name):
        return self.root / "facts" / f"{name}.parquet"

    def _append(self, name, df, keys):
        path = self._fact_path(name)
        if path.exists():
            df = pd.concat([pd.read_parquet(path), df], ignore_index=True)
        present = [k for k in keys if k in df.columns]
        if present:
            df = df.drop_duplicates(subset=present)
        df.to_parquet(path, index=False)
        return df

    def append_cb_detail(self, df):
        return self._append("cb_detail", df, CB_KEYS)

    def append_gross(self, df):
        return self._append("gross", df, GROSS_KEYS)

    def _load(self, name):
        path = self._fact_path(name)
        return pd.read_parquet(path) if path.exists() else pd.DataFrame()

    def load_cb_detail(self):
        return self._load("cb_detail")

    def load_gross(self):
        return self._load("gross")

    def save_v7(self, df):
        df.to_parquet(self._fact_path("v7"), index=False)

    def load_v7(self):
        return self._load("v7")

    # ---- sessions / files ----
    def create_session(self, label, start, end):
        sid = str(uuid.uuid4())
        con = sqlite3.connect(self.db)
        con.execute(
            "INSERT INTO sessions(id,label,date_range_start,date_range_end)"
            " VALUES(?,?,?,?)",
            (sid, label, start, end),
        )
        con.commit()
        con.close()
        return sid

    def add_file(self, session_id, filename, file_type, row_count):
        con = sqlite3.connect(self.db)
        con.execute(
            "INSERT INTO uploaded_files(session_id,filename,file_type,row_count)"
            " VALUES(?,?,?,?)",
            (session_id, filename, file_type, int(row_count)),
        )
        con.commit()
        con.close()

    def list_sessions(self):
        con = sqlite3.connect(self.db)
        con.row_factory = sqlite3.Row
        rows = [
            dict(r)
            for r in con.execute("SELECT * FROM sessions ORDER BY created_at DESC")
        ]
        con.close()
        return rows
