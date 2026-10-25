"""Supervised fraud classifiers: Logistic Regression, Random Forest, XGBoost. Only runs when real fraud labels exist."""
import time
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from xgboost import XGBClassifier

def _metrics(y, pred, score):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    both = len(set(y)) == 2
    return {"accuracy": float(accuracy_score(y, pred)), "precision": float(precision_score(y, pred, zero_division=0)),
            "recall": float(recall_score(y, pred, zero_division=0)), "f1": float(f1_score(y, pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y, score)) if both else None,
            "pr_auc": float(average_precision_score(y, score)) if both else None,
            "cm": [[int(tn), int(fp)], [int(fn), int(tp)]]}

def _period(df, idx):
    d = df.date.iloc[idx].dropna()
    return "n/a" if d.empty else f"{d.min():%Y-%m-%d} to {d.max():%Y-%m-%d}"

def split(df, y):
    """Temporal split (train on the past, test on the future) when dates exist; otherwise stratified random."""
    if df.date.notna().mean() >= .8:
        order = np.argsort(df.date.fillna(pd.Timestamp.max).to_numpy(), kind="stable")
        cut = int(len(df) * .7)
        return order[:cut], order[cut:], "temporal: train on the earlier 70%, test on the later 30%"
    tr, te = train_test_split(np.arange(len(df)), test_size=.3, stratify=y, random_state=7)
    return tr, te, "stratified random (dates missing)"

def evaluate(df, X, rule_score, thr):
    """rule_score: the expert rule score (0-1), used only as the no-learning baseline row; thr: its flag threshold."""
    y = df.label.to_numpy().astype(int)
    if y.sum() == 0:
        return {"available": False, "reason": "No fraud labels found. Add an is_fraud column (1 = confirmed fraud, 0 = not fraud) to measure accuracy."}
    tr, te, how = split(df, y)
    if min(y[tr].sum(), y[te].sum(), (1 - y[tr]).sum(), (1 - y[te]).sum()) < 3:
        return {"available": False, "reason": "Too few fraud or legitimate cases in the training or test period to evaluate fairly."}
    models = {"Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")),
              "Random Forest": RandomForestClassifier(n_estimators=150, max_depth=8, class_weight="balanced", n_jobs=1, random_state=7)}
    models["XGBoost (main model)"] = XGBClassifier(n_estimators=150, max_depth=4, learning_rate=.1, eval_metric="logloss", n_jobs=1, random_state=7,
                  scale_pos_weight=float((y[tr] == 0).sum() / max(y[tr].sum(), 1)))
    rows = []
    for name, m in models.items():
        t = time.time()
        m.fit(X[tr], y[tr])
        sec = round(time.time() - t, 2)
        p = m.predict_proba(X[te])[:, 1]
        rows.append({"name": name, "seconds": sec, **_metrics(y[te], (p >= .5).astype(int), p)})
    rows.append({"name": "Expert rule score (no learning, baseline)", "seconds": None,
                 **_metrics(y[te], (rule_score[te] >= thr).astype(int), rule_score[te])})
    notes = ["Supervised models use a 0.5 probability cut-off; the rule-score baseline row uses its top-5% flag.",
             "Features such as vendor averages are built from the whole file, so a little look-ahead is possible.",
             "Nothing is retrained automatically; new confirmed outcomes should be added to a new labelled file."]
    return {"available": True, "split": how, "train_n": int(len(tr)), "test_n": int(len(te)),
            "train_period": _period(df, tr), "test_period": _period(df, te),
            "train_fraud": int(y[tr].sum()), "test_fraud": int(y[te].sum()), "test_legit": int((1 - y[te]).sum()),
            "baseline_accuracy": float(1 - y[te].mean()), "models": rows, "notes": notes}
