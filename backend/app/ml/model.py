"""Stage 4: XGBoost risk model (gradient-boosted trees).
- Labels available (is_fraud): XGBClassifier. Risk = out-of-fold fraud probability, so no row is scored by a model that saw its own label.
- No labels: XGBRegressor learns the expert rule score (weak labels). This is screening, not measured fraud accuracy."""
import numpy as np
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier, XGBRegressor

PARAMS = dict(n_estimators=200, max_depth=4, learning_rate=.08, subsample=.9, colsample_bytree=.9, n_jobs=1, random_state=7)

def _clf(y):
    return XGBClassifier(**PARAMS, eval_metric="logloss", scale_pos_weight=float((y == 0).sum() / max(y.sum(), 1)))

def train(X, target, y):
    """Returns (final model, risk 0-1 per row, mode). y = 0/1 fraud labels (all zero when none were supplied)."""
    y = np.asarray(y).astype(int)
    if y.sum() >= 10 and (1 - y).sum() >= 10:
        k = int(min(5, y.sum(), (1 - y).sum()))
        oof = np.zeros(len(y))
        for tr, te in StratifiedKFold(k, shuffle=True, random_state=7).split(X, y):
            oof[te] = _clf(y[tr]).fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
        return _clf(y).fit(X, y), oof, "supervised"
    m = XGBRegressor(**PARAMS).fit(X, target)
    return m, np.clip(m.predict(X), 0, 1), "weak-label"

def predict(model, mode, X):
    X = np.atleast_2d(X)
    return model.predict_proba(X)[:, 1] if mode == "supervised" else np.clip(model.predict(X), 0, 1)

def importance(model):
    g = np.asarray(model.feature_importances_, dtype=float)
    return (g / g.sum() if g.sum() > 0 else g).tolist()
