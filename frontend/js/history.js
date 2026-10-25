/* Historical vs Current page. Adds a menu item and wraps page() from app.js. */
NAV.splice(3, 0, ['hist', '🕘', 'Historical vs Current']);
const _page = page;
page = function () { return S.pg == 'hist' ? histPage() : _page(); };
async function histLoad() {
  try { S.hs = await (await api.req('/history/summary')).json(); } catch (e) { S.hs = { rows: 0 }; }
  draw();
}
async function histUpload(file) {
  if (!file) return;
  const fd = new FormData(); fd.append('file', file, file.name);
  try {
    const r = await (await api.req('/history/upload', { method: 'POST', body: fd })).json();
    alert('Historical file loaded: ' + r.added + ' new rows added, ' + r.skipped + ' duplicates skipped.');
  } catch (e) { alert(e.message); }
  histLoad();
}
function histPage() {
  if (S.hs === undefined) { S.hs = { rows: 0 }; histLoad(); }
  const hs = S.hs, R = S.res, h = R && R.hist;
  let o = hd('Historical vs Current', 'Compare new transactions with approved historical records. Nothing is estimated when history is missing.');
  o += `<div class="card" style="margin-bottom:14px"><h2>Historical data store</h2><p>${hs.rows ? hs.rows.toLocaleString('en-IN') + ' records · ' + hs.vendors + ' vendors · ' + (hs.from || 'n/a') + ' to ' + (hs.to || 'n/a') : 'No historical data uploaded yet.'}</p>`
    + `<input id="hf" type="file" accept=".csv,text/csv" style="display:none" onchange="histUpload(this.files[0])"><button class="btn s" onclick="$('#hf').click()">Upload historical CSV</button>`
    + (hs.files && hs.files.length ? tb(['File', 'Rows', 'Added', 'Duplicates skipped', 'Loaded'], hs.files.map(f => `<tr><td>${esc(f.name)}</td><td>${f.rows}</td><td>${f.added}</td><td>${f.skipped}</td><td>${f.loaded_at}</td></tr>`)) : '') + '</div>';
  if (!R) return o + '<div class="card">Run a current analysis (CSV Upload) to see the comparison.</div>';
  if (!h || !h.available) return o + '<div class="card">Historical comparisons are unavailable because no historical transactions are stored. The current file was analysed on its own.</div>';
  o += `<div class="g">${kp('Historical transactions', h.hist_n)}${kp('Current transactions', h.cur_n)}${kp('Historical period', h.hist_from + ' → ' + h.hist_to)}${kp('Current period', h.cur_from + ' → ' + h.cur_to)}${kp('Avg monthly spend (hist)', fm(h.hist_monthly_avg))}${kp('Avg monthly spend (current)', fm(h.cur_monthly_avg))}</div>`;
  const shift = (t, a) => `<div class="card" style="margin-bottom:14px"><h2>${t}</h2>${a.length ? tb(['Name', 'Hist monthly spend', 'Current monthly spend', 'Hist txns/month', 'Current txns/month'], a.map(x => `<tr><td>${esc(x.name)}</td><td>${fm(x.hist_spend)}</td><td>${fm(x.cur_spend)}</td><td>${x.hist_n.toFixed(1)}</td><td>${x.cur_n.toFixed(1)}</td></tr>`)) : '<p class="m">No unusual change found (needs 3+ months of history).</p>'}</div>`;
  o += `<div class="card" style="margin-bottom:14px"><h2>Payments far from the vendor’s historical amounts</h2>${h.amount_flags.length ? tb(['ID', 'Vendor', 'Amount', 'Vendor hist. typical', 'Deviation (z)'], h.amount_flags.map(x => `<tr><td>${esc(x.id)}</td><td>${esc(x.vendor)}</td><td>${fm(x.amount)}</td><td>${fm(x.hist_avg)}</td><td>${x.z.toFixed(1)}</td></tr>`)) : '<p class="m">None found.</p>'}</div>`;
  o += `<div class="card" style="margin-bottom:14px"><h2>Invoices already recorded in history</h2>${h.repeated_invoices.length ? tb(['ID', 'Vendor', 'Invoice', 'Amount'], h.repeated_invoices.map(x => `<tr><td>${esc(x.id)}</td><td>${esc(x.vendor)}</td><td>${esc(x.invoice)}</td><td>${fm(x.amount)}</td></tr>`)) : '<p class="m">None found (needs an invoice column).</p>'}</div>`;
  o += shift('Vendor spending changes', h.vendor_shift) + shift('Employee-associated transaction changes', h.employee_shift);
  return o + `<p class="m">Limitations: ${h.new_vendors} current payments are to vendors with no history, and ${h.thin_vendors} are to vendors with fewer than 5 past payments, so their amounts were not compared. These flags are review prompts, not proof of fraud.</p>`;
}
