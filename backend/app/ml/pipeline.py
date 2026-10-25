"""End-to-end audit pipeline: clean -> features -> sliding windows -> VAE + GRU + temporal attention -> SHAP -> scores -> recommendations."""
import json
import numpy as np
import pandas as pd
from . import scoring as sc
from .explain import explain
from .historical import compare, historical_recs
from .features import FEATURES, W, build
from .model import T, predict, score_windows, train
from .preprocess import clean

def _records(df):
    return json.loads(df.to_json(orient="records"))

SHAP_ROWS = 15  # SHAP is computed for the 15 highest-risk transactions
_log = lambda m: print(f"[audit] {m}", flush=True)

def _windows(df):
    """Row ids of the last T transactions in time order for every transaction (padded with the first row)."""
    n = len(df)
    order = np.argsort(df.date.fillna(pd.Timestamp.max).to_numpy(), kind="stable")
    pos = np.empty(n, dtype=int)
    pos[order] = np.arange(n)
    return order[np.clip(np.arange(n)[:, None] + np.arange(-T + 1, 1), 0, None)][pos]

def run(raw, history=None):
    df, log, has_approver = clean(raw)
    if len(df) < 10:
        raise ValueError("Need at least 10 valid rows.")
    X = build(df)
    rule = X @ W
    Q = float(np.quantile(rule, .995))
    Q = Q if Q > 0 else 1.0
    target = np.clip(rule / Q, 0, 1)                                 # weak labels from the expert rule score
    if df.label.sum() > 0:                                           # use real labels when the CSV has them
        target = np.where(df.label.to_numpy() > 0, 1.0, target)
    _log(f"{len(df)} rows cleaned, features built; training VAE+GRU")
    win = _windows(df)
    model = train(X, win, target)
    _log("training done; scoring")
    head, err, att = predict(model, X, win)
    E = float(np.quantile(err, .99)) or 1.0
    E = E if E > 0 else 1.0

    def mix(rule_part, h, e):                     # 50% expert rule score + 50% VAE/GRU model score
        return .5 * np.clip(rule_part, 0, 1) + .5 * (.6 * h + .4 * np.clip(e / E, 0, 1))

    risk = mix(rule / Q, head, err)

    def make_fn(i):                               # score of row i's window when only its own features change (for SHAP)
        ctx = X[win[i, :-1]]

        def f(Z):
            Z = np.atleast_2d(np.asarray(Z, dtype=float))
            xb = np.concatenate([np.repeat(ctx[None], len(Z), 0), Z[:, None, :]], axis=1)
            h, e, _ = score_windows(model, xb)
            return mix(Z @ W / Q, h, e)
        return f

    attention = att.mean(0)
    df["risk"] = risk
    thr = float(max(np.quantile(risk, .95), .4))
    flagged = np.where(risk >= thr)[0]
    top = flagged[np.argsort(-risk[flagged])][:1000]
    df["ty"] = np.array(FEATURES)[(X * W).argmax(1)]
    _log("scoring done; running SHAP")
    shap_rows = explain(make_fn, X, top[:SHAP_ROWS], X.mean(0))
    _log("SHAP done; building scores")

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
            "recs": sc.recommendations(len(flagged), exposure, top5, comp, vend, emp) + historical_recs(hist), "hist": hist,
            "vend": _records(vend), "emp": _records(emp), "A": attention.tolist(), "win": T, "model": "VAE + GRU + Temporal Attention",
            "hist": np.histogram(risk, bins=10, range=(0, 1))[0].tolist(),
            "rows": rows, "X": X[top].tolist(), "fl": list(range(len(rows))), "shap": shap_rows,
            "nfl": int(len(flagged)), "thr": thr}
