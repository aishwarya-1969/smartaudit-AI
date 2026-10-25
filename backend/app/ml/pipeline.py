"""End-to-end audit pipeline: clean -> features -> XGBoost -> SHAP (TreeExplainer) -> scores -> recommendations."""
import json
import numpy as np
import pandas as pd
from . import scoring as sc
from .explain import explain
from .supervised import evaluate
from .historical import compare, historical_recs
from .features import FEATURES, W, build
from .model import importance, train
from .preprocess import clean

def _records(df):
    return json.loads(df.to_json(orient="records"))

SHAP_ROWS = 15  # SHAP is computed for the 15 highest-risk transactions
_log = lambda m: print(f"[audit] {m}", flush=True)

def run(raw, history=None):
    df, log, has_approver = clean(raw)
    if len(df) < 10:
        raise ValueError("Need at least 10 valid rows.")
    X = build(df)
    rule = X @ W
    Q = float(np.quantile(rule, .995))
    Q = Q if Q > 0 else 1.0
    target = np.clip(rule / Q, 0, 1)                                 # weak labels from the expert rule score
    _log(f"{len(df)} rows cleaned, features built; training XGBoost")
    model, risk, mode = train(X, target, df.label.to_numpy())
    _log(f"training done ({mode}); scoring")
    importance_ = importance(model)

    df["risk"] = risk
    thr = float(max(np.quantile(risk, .95), .4))
    flagged = np.where(risk >= thr)[0]
    top = flagged[np.argsort(-risk[flagged])][:1000]
    df["ty"] = np.array(FEATURES)[(X * W).argmax(1)]
    _log("scoring done; running SHAP")
    shap_rows = explain(model, mode, X, top[:SHAP_ROWS], X)
    _log("SHAP done; building scores")

    try:
        evaluation = evaluate(df, X, np.clip(rule / Q, 0, 1), float(np.quantile(np.clip(rule / Q, 0, 1), .95)))
    except Exception as e:
        evaluation = {"available": False, "reason": f"Evaluation failed: {e}"}
    vend, emp = sc.vendors(df, thr), sc.employees(df, thr)
    comp, cs = sc.compliance(df, X, has_approver)
    total, exposure = float(df.amount.sum()), float(df.amount[risk >= thr].sum())
    hc, hs = sc.health(log, cs, vend, emp, exposure, total)
    top5 = float(df.amount.iloc[top[:5]].sum())
    rows = [{"id": str(df.id.iloc[i]), "d": None if pd.isna(df.date.iloc[i]) else df.date.iloc[i].strftime("%Y-%m-%d"),
             "v": df.vendor.iloc[i], "e": df.employee.iloc[i], "a": float(df.amount.iloc[i]),
             "r": float(risk[i]), "ty": df.ty.iloc[i]} for i in top]
    hist = compare(df, history)
    return {"n": len(df), "L": log, "comp": comp, "cs": cs, "tot": total, "exp": exposure, "hc": hc, "hs": hs,
            "recs": sc.recommendations(len(flagged), exposure, top5, comp, vend, emp) + historical_recs(hist), "history": hist, "evaluation": evaluation,
            "vend": _records(vend), "emp": _records(emp), "A": importance_, "model": "XGBoost", "mode": mode,
            "hist": np.histogram(risk, bins=10, range=(0, 1))[0].tolist(),
            "rows": rows, "X": X[top].tolist(), "fl": list(range(len(rows))), "shap": shap_rows,
            "nfl": int(len(flagged)), "thr": thr}
