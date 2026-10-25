"""Stage 6: SHAP for the highest-risk transactions. The 7 earlier transactions in the window stay fixed as context."""
import numpy as np
import shap

def explain(make_fn, X, idx, baseline):
    out = []
    for i in idx:
        f = make_fn(i)
        ex = shap.KernelExplainer(f, baseline.reshape(1, -1))
        sv = np.asarray(ex.shap_values(X[i:i + 1], nsamples=256, silent=True)).reshape(-1)
        out.append({"phi": sv.tolist(), "base": float(np.ravel(ex.expected_value)[0]), "out": float(f(X[i:i + 1])[0])})
    return out
