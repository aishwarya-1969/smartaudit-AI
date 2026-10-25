"""Run:  python tests/test_supervised.py   (from the backend folder)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np, pandas as pd
from app.ml.features import W, build
from app.ml.preprocess import clean
from app.ml.supervised import evaluate

def load(path):
    df, _, _ = clean(pd.read_csv(path, dtype=str, keep_default_na=False))
    X = build(df)
    return df, X, np.clip(X @ W / np.quantile(X @ W, .995), 0, 1)

DEMO = os.path.join(os.path.dirname(__file__), "..", "..", "sample_data", "labeled_demo.csv")

def test_labelled_demo_reports_real_metrics():
    df, X, risk = load(DEMO)
    ev = evaluate(df, X, risk, .4)
    assert ev["available"] and ev["split"].startswith("temporal")
    assert ev["train_period"].split(" to ")[1] <= ev["test_period"].split(" to ")[0]   # no future data in training
    for m in ev["models"]:
        assert 0 <= m["accuracy"] <= 1 and sum(map(sum, m["cm"])) == ev["test_n"]

def test_no_labels_means_no_metrics():
    df, X, risk = load(DEMO)
    df["label"] = 0.0
    ev = evaluate(df, X, risk, .4)
    assert ev["available"] is False and "is_fraud" in ev["reason"]

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)
