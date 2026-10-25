/* Model Evaluation page (Logistic Regression, Random Forest, XGBoost (main model) vs the expert rule score). Shows only real measured metrics. */
NAV.splice(4, 0, ['eval', '📈', 'Model Evaluation']);
const _page2 = page;
page = function () { return S.pg == 'eval' ? evalPage() : _page2(); };
function evalPage() {
  const R = S.res, ev = R && R.evaluation;
  const pc = v => v == null ? 'n/a' : (v * 100).toFixed(1) + '%';
  let o = hd('Model Evaluation', 'Real test results on held-out data. Nothing here is estimated or hard-coded.');
  if (!R) return o + '<div class="card">Run an analysis first (CSV Upload).</div>';
  if (!ev || !ev.available) return o + `<div class="card"><p>${esc((ev && ev.reason) || 'Evaluation unavailable.')}</p><p class="m">Without labels, XGBoost learns from the expert rule score (weak labels), so its output is a screening score that ranks what to investigate first and no accuracy is shown. Try sample_data/labeled_demo.csv to see Logistic Regression, Random Forest and XGBoost.</p></div>`;
  o += `<div class="g">${kp('Train rows', ev.train_n)}${kp('Test rows', ev.test_n)}${kp('Test fraud cases', ev.test_fraud, 'var(--r)')}${kp('Test legitimate', ev.test_legit)}</div>`;
  o += `<div class="card" style="margin-bottom:14px"><p><b>Split:</b> ${esc(ev.split)}<br><b>Train period:</b> ${ev.train_period} · <b>Test period:</b> ${ev.test_period}</p><p class="m" style="margin:0">A model that calls every transaction legitimate would already score ${pc(ev.baseline_accuracy)} accuracy, so judge models by precision, recall, F1 and PR-AUC, not accuracy alone.</p></div>`;
  o += `<div class="card" style="margin-bottom:14px"><h2>Results on the test set</h2>${tb(['Model', 'Accuracy', 'Precision', 'Recall', 'F1', 'ROC-AUC', 'PR-AUC', 'TN / FP / FN / TP', 'Train time'], ev.models.map(m => `<tr><td>${esc(m.name)}</td><td>${pc(m.accuracy)}</td><td>${pc(m.precision)}</td><td>${pc(m.recall)}</td><td>${pc(m.f1)}</td><td>${pc(m.roc_auc)}</td><td>${pc(m.pr_auc)}</td><td>${m.cm[0][0]} / ${m.cm[0][1]} / ${m.cm[1][0]} / ${m.cm[1][1]}</td><td>${m.seconds == null ? '-' : m.seconds + ' s'}</td></tr>`))}</div>`;
  o += `<div class="card"><h2>How to read this</h2><p class="m" style="margin:0"><b>Precision:</b> of the transactions flagged as fraud, how many really were. <b>Recall:</b> of the real fraud, how many were caught. <b>F1:</b> balance of both. <b>ROC-AUC / PR-AUC:</b> how well the score ranks fraud above legitimate (PR-AUC matters most when fraud is rare).</p><ul>${ev.notes.map(n => `<li>${esc(n)}</li>`).join('')}</ul></div>`;
  return o;
}
