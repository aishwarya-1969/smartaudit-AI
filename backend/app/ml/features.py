"""Stage 3: feature engineering (9 audit risk indicators scaled to 0-1)."""
import numpy as np

FEATURES = ["Amount outlier", "Abnormal for vendor", "Abnormal for employee", "Round-sum payment",
            "Weekend / off-hours", "Benford irregularity", "Unknown / rare vendor",
            "Threshold structuring", "Duplicate payment"]
PRIOR = np.array([.9, 1, .9, .5, .5, .35, .7, .9, 1.])
W = PRIOR / PRIOR.sum()  # expert prior used for the rule score / weak labels
LIMITS = [1000, 5000, 10000, 25000, 50000]

def build(df):
    a = df.amount.to_numpy(float)
    la = np.log1p(a)
    f = np.zeros((len(df), 9))
    f[:, 0] = np.clip(abs(la - la.mean()) / (la.std() or 1) / 3, 0, 1)
    for j, key in ((1, "vendor"), (2, "employee")):
        g = df.assign(la=la).groupby(key)["la"]
        sd = g.transform("std").fillna(0).clip(lower=.3)
        f[:, j] = np.where(g.transform("count") >= 3, np.clip(abs(la - g.transform("mean")) / sd / 3, 0, 1), 0)
    f[:, 3] = np.where((a % 1000 == 0) & (a >= 1000), 1, np.where((a % 100 == 0) & (a >= 500), .6, 0))
    weekend = df.date.dt.dayofweek.isin([5, 6]).to_numpy()
    offhrs = (df.has_time & ((df.date.dt.hour < 6) | (df.date.dt.hour >= 22))).to_numpy()
    f[:, 4] = np.where(weekend, 1, np.where(offhrs, .7, 0))
    fd = (a / 10 ** np.floor(np.log10(np.maximum(a, 1)))).astype(int)
    fd = np.where(a >= 1, fd, 0)
    obs = np.bincount(fd, minlength=10) / len(a)
    exp = np.log10(1 + 1 / np.maximum(np.arange(10), 1))
    f[:, 5] = np.where(fd > 0, np.clip(abs(obs[fd] - exp[fd]) / exp[fd] / 1.5, 0, 1), 0)
    cnt = df.groupby("vendor")["amount"].transform("count").to_numpy()
    f[:, 6] = np.where(df.vendor == "Unknown", 1, np.where(cnt <= 2, .8, np.where(cnt < 5, .4, 0)))
    f[:, 7] = np.any([(a >= .9 * t) & (a < t) for t in LIMITS], axis=0)
    key = df.vendor + "|" + df.amount.astype(str) + "|" + df.date.astype(str)
    f[:, 8] = (key.map(key.value_counts()) > 1).astype(float)
    return f
