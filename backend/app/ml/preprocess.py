"""Stage 2: data preprocessing and cleaning."""
import re
import numpy as np
import pandas as pd

PATTERNS = [("label", r"^(is_)?fraud$|^label$"), ("amount", r"amount|amt|value|total"), ("invoice", r"invoice|inv[_ ]?n|bill"), ("id", r"id|ref|txn"),
            ("date", r"date|time"), ("vendor", r"vendor|supplier|payee|merchant"),
            ("employee", r"employee|staff|user|requester|created|clerk|officer"),
            ("category", r"categ|account|dept"), ("approver", r"approv")]

def _map_columns(cols):
    mapping, used = {}, set()
    for key, pat in PATTERNS:
        mapping[key] = next((c for c in cols if c not in used and re.search(pat, c)), None)
        used.add(mapping[key])
    return mapping

def clean(raw):
    df = raw.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    m = _map_columns(list(df.columns))
    if not m["amount"]:
        raise ValueError("No amount column found. Expected a header such as amount, amt or value.")
    amt = pd.to_numeric(df[m["amount"]].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
    ok = amt.notna()
    log = {"raw": len(df), "miss": int((~ok).sum()), "neg": int((amt[ok] < 0).sum()), "dt": 0, "vn": 0, "en": 0}
    df, amt = df[ok].reset_index(drop=True), amt[ok].abs().reset_index(drop=True)
    col = lambda k: df[m[k]].astype(str).str.strip() if m[k] else pd.Series([""] * len(df))
    ids = pd.Series(np.arange(1, len(df) + 1).astype(str))
    out = pd.DataFrame({"id": col("id").where(col("id") != "", ids) if m["id"] else ids, "amount": amt})
    raw_date = col("date")
    out["date"] = pd.to_datetime(raw_date, errors="coerce", format="mixed")
    out["has_time"] = raw_date.str.contains(r"\d:\d")
    log["dt"] = int(out.date.isna().sum()) if m["date"] else 0
    v, e = col("vendor"), col("employee")
    log["vn"] = int((v == "").sum()) if m["vendor"] else 0
    log["en"] = int((e == "").sum()) if m["employee"] else 0
    out["vendor"] = v.replace("", "Unknown") if m["vendor"] else "All payees"
    out["employee"] = e.replace("", "Unassigned")
    out["category"] = col("category")
    out["invoice"] = col("invoice")
    out["approver"] = col("approver")
    out["label"] = pd.to_numeric(col("label"), errors="coerce").fillna(0).clip(0, 1) if m["label"] else 0.0
    return out, log, m["approver"] is not None
