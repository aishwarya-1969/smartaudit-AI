"""Run:  python tests/test_historical.py   (from the backend folder)"""
import os, sys, tempfile
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np, pandas as pd
from app.db import init
from app.ml import historical as H

def frame(rows):
    df = pd.DataFrame(rows, columns=["id", "date", "vendor", "employee", "amount", "invoice"])
    df["date"] = pd.to_datetime(df.date); df["label"] = 0.0
    return df

def hist_rows(n=12):
    return [(f"H{i}", f"2026-{1 + i % 6:02d}-10", "Acme", "Ravi", 1000.0 + i, f"INV{i}") for i in range(n)]

def test_overlap_is_not_double_counted():
    init(); df = frame(hist_rows())
    assert H.store(df, "a.csv", "u")["added"] == 12
    r = H.store(df, "again.csv", "u")
    assert r["added"] == 0 and r["skipped"] == 12 and H.summary()["rows"] == 12

def test_no_history_means_unavailable():
    assert H.compare(frame(hist_rows()), None) == {"available": False}

def test_repeated_invoice_and_amount_deviation():
    cur = frame([("C1", "2026-08-01", "Acme", "Ravi", 1000.0, "INV3"), ("C2", "2026-08-02", "Acme", "Ravi", 90000.0, "INV99")])
    out = H.compare(cur, frame(hist_rows()))
    assert [x["id"] for x in out["repeated_invoices"]] == ["C1"]
    assert [x["id"] for x in out["amount_flags"]] == ["C2"]

def test_new_vendor_is_not_flagged_as_deviation():
    cur = frame([("C3", "2026-08-01", "NewCo", "Ravi", 500000.0, "X1")])
    out = H.compare(cur, frame(hist_rows()))
    assert out["amount_flags"] == [] and out["new_vendors"] == 1 and out["thin_vendors"] == 1

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)
