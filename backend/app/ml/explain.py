"""Stage 6: SHAP for the highest-risk transactions using TreeExplainer (exact for XGBoost). Explains association, not causation."""
import numpy as np
import shap
from .model import predict

def explain(model, mode, X, idx, background):
    if len(idx) == 0:
        return []
    bg = background[np.random.default_rng(7).permutation(len(background))[:100]]
    ex = (shap.TreeExplainer(model, data=bg, feature_perturbation="interventional", model_output="probability")
          if mode == "supervised" else shap.TreeExplainer(model))
    sv = np.asarray(ex.shap_values(X[idx])).reshape(len(idx), -1)
    base, out = float(np.ravel(ex.expected_value)[0]), predict(model, mode, X[idx])
    return [{"phi": sv[k].tolist(), "base": base, "out": float(out[k])} for k in range(len(idx))]
