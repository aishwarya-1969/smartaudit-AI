"""Stages 7-9: vendor trust, employee risk, compliance, financial health, recommendations."""
import numpy as np

def _agg(df, key, thr):
    g = df.assign(fl=df.risk >= thr).groupby(key).agg(n=("amount", "size"), tot=("amount", "sum"),
                                                      ar=("risk", "mean"), fl=("fl", "sum")).reset_index()
    g["fr"] = g.fl / g.n
    return g.rename(columns={key: "name"})

def vendors(df, thr):
    g = _agg(df, "vendor", thr)
    g["sc"] = np.clip(100 - 130 * g.ar - 160 * g.fr - np.where(g.name == "Unknown", 25, 0), 0, 100).round().astype(int)
    return g.sort_values("sc").reset_index(drop=True)

def employees(df, thr):
    g = _agg(df, "employee", thr)
    g["sc"] = np.clip(100 * (1.6 * g.ar + 2.2 * g.fr), 0, 100).round().astype(int)
    return g.sort_values("sc", ascending=False).reset_index(drop=True)

RULES = ["Approval present for payments above ₹10,000", "No weekend or off-hours postings", "No duplicate payments",
         "No payments just under approval limits", "Every payment linked to a known vendor",
         "No split transactions (same vendor, employee, day)"]

def compliance(df, X, has_approver):
    g = df.assign(day=df.date.dt.strftime("%Y-%m-%d")).groupby(["vendor", "employee", "day"])["amount"]
    split = (g.transform("count") > 1) & (g.transform("max") < 5000) & (g.transform("sum") >= 5000) & df.date.notna()
    fails = [(df.amount > 10000) & (df.approver == ""), X[:, 4] == 1, X[:, 8] > 0, X[:, 7] > 0,
             df.vendor == "Unknown", split]
    out = []
    for i, (name, mask) in enumerate(zip(RULES, fails)):
        c = int(np.asarray(mask).sum())
        out.append({"n": name, "f": c, "ok": None if (i == 0 and not has_approver) else 1 - c / len(df)})
    return out, float(np.mean([r["ok"] for r in out if r["ok"] is not None]))

def health(log, comp_score, vend, emp, exposure, total):
    dq = min(1, max(0, 1 - (log["miss"] + .5 * (log["dt"] + log["vn"] + log["en"])) / log["raw"]))
    fx = min(1, max(0, 1 - exposure / total * 4))
    vt, ctl = float(vend.sc.mean()) / 100, 1 - float((emp.sc >= 60).mean())
    hc = [["Data quality", dq], ["Fraud exposure control", fx], ["Compliance", comp_score],
          ["Vendor reliability", vt], ["Internal control strength", ctl]]
    return hc, int(round(100 * (.15 * dq + .3 * fx + .25 * comp_score + .15 * vt + .15 * ctl)))

def recommendations(nfl, exposure, top5, comp, vend, emp):
    fm = lambda x: f"₹{x:,.0f}"
    r = []
    if nfl:
        r.append(["High", f"Investigate the {nfl} flagged transactions (exposure {fm(exposure)}), starting with the top 5 worth {fm(top5)}."])
    if comp[2]["f"]:
        r.append(["High", f"Place {comp[2]['f']} suspected duplicate payments on hold and request vendor credit notes or reversals."])
    if comp[3]["f"]:
        r.append(["High", f"{comp[3]['f']} payments sit just below approval limits. Review for threshold structuring and tighten delegation limits."])
    for _, v in vend[vend.sc < 60].head(3).iterrows():
        r.append(["Medium", f'Re-verify vendor "{v["name"]}" (trust {v.sc}/100): confirm KYC, bank details and contract.'])
    for _, e in emp[emp.sc >= 60].head(3).iterrows():
        r.append(["Medium", f"Run a focused review of {e['name']}’s postings (risk {e.sc}/100) and enforce segregation of duties."])
    if comp[1]["f"]:
        r.append(["Low", f"Restrict system posting on weekends and require justification for off-hours entries ({comp[1]['f']} found)."])
    return r or [["Low", "No significant risk detected. Continue periodic sampling."]]
