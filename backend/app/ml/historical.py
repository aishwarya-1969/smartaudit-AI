"""Historical storage (de-duplicated) and historical-vs-current comparison. Never invents history."""
import hashlib
import numpy as np
import pandas as pd
from ..db import conn

MIN_VENDOR_HISTORY = 5   # a vendor needs this many past payments before amounts are compared
MIN_MONTHS = 3           # months of history needed before monthly spend/frequency is compared

def make_keys(df):
    d = df.date.dt.strftime("%Y-%m-%d").fillna("")
    raw = df.id + "|" + d + "|" + df.vendor + "|" + df.amount.round(2).astype(str) + "|" + df.invoice
    return raw.map(lambda s: hashlib.sha256(s.encode()).hexdigest())

def store(df, filename, user):
    df = df.assign(k=make_keys(df))
    with conn() as c:
        have = {r[0] for r in c.execute("select k from history")}
        new = df[~df.k.isin(have)].drop_duplicates("k")
        c.executemany("insert into history values(?,?,?,?,?,?,?,?,?,?)",
                      [(r.k, r.id, "" if pd.isna(r.date) else r.date.strftime("%Y-%m-%d"), r.vendor, r.employee,
                        float(r.amount), r.invoice, float(r.label), filename, user) for r in new.itertuples()])
        c.execute("insert into history_files values(?,?,?,?,?,datetime('now'))",
                  (filename, user, len(df), len(new), len(df) - len(new)))
    return {"rows": len(df), "added": len(new), "skipped": len(df) - len(new)}

def load():
    with conn() as c:
        h = pd.read_sql_query("select id,date,vendor,employee,amount,invoice,label from history", c)
    h["date"] = pd.to_datetime(h.date, errors="coerce")
    return h if len(h) else None

def summary():
    with conn() as c:
        n, lo, hi, v = c.execute("select count(*), min(nullif(date,'')), max(nullif(date,'')), count(distinct vendor) from history").fetchone()
        files = [dict(r) for r in c.execute("select name, rows, added, skipped, loaded_at from history_files order by rowid desc limit 8")]
    return {"rows": n, "from": lo, "to": hi, "vendors": v, "files": files}

def _shift(cur, hist, key):
    def monthly(d):
        d = d.dropna(subset=["date"]).assign(m=lambda x: x.date.dt.to_period("M"))
        return d.groupby([key, "m"]).amount.agg(["sum", "size"]).reset_index()
    h, c = monthly(hist), monthly(cur)
    if h.empty or c.empty:
        return []
    base = h.groupby(key).agg(months=("m", "nunique"), hs=("sum", "mean"), hn=("size", "mean"))
    now = c.groupby(key).agg(cs=("sum", "mean"), cn=("size", "mean"))
    j = now.join(base, how="inner")
    j = j[(j.months >= MIN_MONTHS) & ((j.cs / j.hs >= 2) | (j.cn / j.hn >= 2))].sort_values("cs", ascending=False).head(10)
    return [{"name": str(k), "hist_spend": float(r.hs), "cur_spend": float(r.cs), "hist_n": float(r.hn), "cur_n": float(r.cn)}
            for k, r in j.iterrows()]

def compare(cur, hist):
    if hist is None or len(hist) == 0:
        return {"available": False}
    st = hist.assign(l=np.log1p(hist.amount)).groupby("vendor")["l"].agg(["mean", "std", "count"])
    mean, cnt = cur.vendor.map(st["mean"]), cur.vendor.map(st["count"]).fillna(0)
    z = (np.log1p(cur.amount) - mean) / cur.vendor.map(st["std"]).fillna(0).clip(lower=.3)
    bad = (cnt >= MIN_VENDOR_HISTORY) & (z.abs() >= 3)
    amount_flags = [{"id": r.id, "vendor": r.vendor, "amount": float(r.amount), "hist_avg": float(np.expm1(mean[i])), "z": float(z[i])}
                    for i, r in cur[bad].head(100).iterrows()]
    seen = set(hist.invoice[hist.invoice != ""])
    rep = cur[(cur.invoice != "") & cur.invoice.isin(seen)]
    repeated = [{"id": r.id, "vendor": r.vendor, "invoice": r.invoice, "amount": float(r.amount)} for r in rep.head(100).itertuples()]
    def span(d):
        x = d.date.dropna()
        return (x.min().strftime("%Y-%m-%d"), x.max().strftime("%Y-%m-%d"), x.dt.to_period("M").nunique()) if len(x) else ("n/a", "n/a", 0)
    hf, ht, hm = span(hist)
    cf, ct, cm = span(cur)
    hist_total = float(hist.amount[hist.date.notna()].sum())
    cur_total = float(cur.amount[cur.date.notna()].sum())
    return {"available": True, "hist_n": len(hist), "cur_n": len(cur), "hist_from": hf, "hist_to": ht, "cur_from": cf, "cur_to": ct,
            "hist_monthly_avg": hist_total / hm if hm else 0.0, "cur_monthly_avg": cur_total / cm if cm else 0.0,
            "amount_flags": amount_flags, "repeated_invoices": repeated,
            "new_vendors": int((~cur.vendor.isin(st.index)).sum()), "thin_vendors": int((cnt < MIN_VENDOR_HISTORY).sum()),
            "vendor_shift": _shift(cur, hist, "vendor"), "employee_shift": _shift(cur, hist, "employee")}

def historical_recs(h):
    if not h.get("available"):
        return []
    r = []
    if h["repeated_invoices"]:
        r.append(["High", f"{len(h['repeated_invoices'])} invoice numbers were already recorded in historical data. Compare the documents and payment records before accepting them."])
    if h["amount_flags"]:
        r.append(["Medium", f"{len(h['amount_flags'])} payments differ strongly from that vendor's historical amounts. Check invoice, purchase order and supporting documents."])
    return r
