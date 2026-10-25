/* ============================================================
 * SmartAudit AI - UI layer (js/app.js)
 * Sections, top to bottom:
 *   1. Helpers      formatting, math, escaping, local storage
 *   2. App state    S = current user, page, analysis result
 *   3. Navigation   NAV menu, pipeline STEPS, go()
 *   4. Sample data  sample() builds a demo CSV; load() runs the pipeline
 *   5. UI builders  tables, bars, gauge, KPI cards
 *   6. page()       one block per module (upload, clean, fraud, shap,
 *                   vendor, emp, comp, health, dash, users)
 *   7. draw()       login screen and app shell
 * The analysis itself runs on the Python backend (see js/api.js).
 * ============================================================ */

const $ = s => document.querySelector(s);
const mem = {};
const LS = {
    g(k) {
        try {
            return localStorage.getItem(k);
        }
        catch (e) {
            return mem[k] || null;
        }
    }, s(k, v) {
        try {
            localStorage.setItem(k, v);
        }
        catch (e) {
            mem[k] = v;
        }
    }
};
const fm = n => '₹' + Math.round(n).toLocaleString('en-IN');
const avg = a => a.reduce((x, y) => x + y, 0) / (a.length || 1);
const sd = a => {
    const m = avg(a);
    return Math.sqrt(avg(a.map(x => (x - m) ** 2)));
};
const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const qt = (a, p) => [...a].sort((x, y) => x - y)[Math.floor(p * (a.length - 1))];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
}[c]));
const mb = a => () => {
    a |= 0;
    a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
};
const FN = ['Amount outlier', 'Abnormal for vendor', 'Abnormal for employee', 'Round-sum payment', 'Weekend / off-hours', 'Benford irregularity', 'Unknown / rare vendor', 'Threshold structuring', 'Duplicate payment'];
const NAV = [
    ['upload', '⬆️', 'CSV Upload'], ['clean', '🧹', 'Data Cleaning'], ['fraud', '🛡️', 'Fraud Detection'], ['shap', '🔍', 'SHAP Explainability'], ['vendor', '🏢', 'Vendor Trust Score'], ['emp', '👤', 'Employee Risk'], ['comp', '✅', 'Compliance Monitoring'], ['health', '💚', 'Financial Health'], ['dash', '📊', 'Dashboard & PDF'], ['users', '⚙️', 'User Management']
];
const STEPS = ['Dataset upload', 'Data preprocessing', 'Feature engineering', 'VAE + GRU + Temporal Attention', 'Anomaly detection', 'SHAP explainable AI', 'Fraud detection', 'Risk score generation', 'Audit recommendations'];
let S = {
    u: null, pg: 'upload', res: null, sel: 0, busy: -1, reg: 0, err: '', cache: {}
};
const users = () => {
    try {
        return JSON.parse(LS.g('sa_users') || '{}');
    }
    catch (e) {
        return {};
    }
};
async function H(s) {
    try {
        const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
        return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
    }
    catch (e) {
        return btoa(s);
    }
}
async function auth() {
    const n = $('#un').value.trim().toLowerCase();
    const p = $('#pw').value;
    const U = users();
    if (!n || p.length < 4) {
        S.err = 'Enter a username and a password of 4+ characters';
        return draw();
    }
    const h = await H(p);
    if (S.reg) {
        if (U[n]) {
            S.err = 'That user already exists';
            return draw();
        }
        U[n] = {
            h, role: Object.keys(U).length ? 'Auditor' : 'Admin'
        };
        LS.s('sa_users', JSON.stringify(U));
    }
    else if (!U[n] || U[n].h !== h) {
        S.err = 'Invalid username or password';
        return draw();
    }
    S.u = {
        n, role: U[n].role
    };
    S.err = '';
    LS.s('sa_sess', n);
    draw();
}
const go = async (p) => {
    if (p == 'users')
        await api.users();
    S.pg = p;
    draw();
    scrollTo(0, 0);
};
function csv(t) {
    const r = [];
    let c = [];
    let f = '';
    let q = 0;
    for (let i = 0; i < t.length; i++) {
        const h = t[i];
        if (q) {
            if (h == '"') {
                if (t[i + 1] == '"') {
                    f += '"';
                    i++;
                }
                else
                    q = 0;
            }
            else
                f += h;
        }
        else if (h == '"')
            q = 1;
        else if (h == ',') {
            c.push(f);
            f = '';
        }
        else if (h == '\n' || h == '\r') {
            if (h == '\r' && t[i + 1] == '\n')
                i++;
            c.push(f);
            r.push(c);
            c = [];
            f = '';
        }
        else
            f += h;
    }
    if (f || c.length) {
        c.push(f);
        r.push(c);
    }
    return r.filter(x => x.some(y => y.trim()));
}
function sample() {
    const r = mb(42);
    const rn = () => Math.sqrt(-2 * Math.log(r() + 1e-9)) * Math.cos(6.283 * r());
    const V = ['Acme Supplies', 'Globex Logistics', 'Initech IT', 'Umbrella Chemicals', 'Stark Industries', 'Wayne Facilities', 'Hooli Cloud', 'Vandelay Imports', 'Soylent Foods', 'Wonka Packaging', 'Pied Piper', 'Cyberdyne Systems'];
    const E = ['Anita', 'Ravi', 'Meena', 'Karthik', 'Divya', 'Suresh', 'Priya', 'Arjun'];
    const C = ['Travel', 'Software', 'Logistics', 'Facilities', 'Consulting'];
    const p2 = n => String(n).padStart(2, '0');
    const ds = d => d.getFullYear() + '-' + p2(d.getMonth() + 1) + '-' + p2(d.getDate());
    let o = 'txn_id,date,vendor,employee,category,amount,approved_by';
    let last = '';
    for (let i = 1; i <= 1200; i++) {
        let vi = Math.floor(r() * V.length);
        let d = new Date(2026, 0, 1 + Math.floor(r() * 270));
        if (d.getDay() % 6 == 0 && r() < .9)
            d.setDate(d.getDate() + 2);
        let v = V[vi];
        let e = E[Math.floor(r() * E.length)];
        let a = Math.round(600 * (1 + vi * .6) * Math.exp(rn() * .45) * 100) / 100;
        let k = i % 24;
        if (k == 3)
            a = [4975, 4990, 9950, 9985][Math.floor(r() * 4)];
        if (k == 7) {
            a = 50000;
            d = new Date(2026, Math.floor(r() * 9), 7 + 7 * Math.floor(r() * 3));
            while (d.getDay())
                d.setDate(d.getDate() + 1);
            v = r() < .5 ? '' : 'Quick Fix Traders';
            e = 'Karthik';
        }
        if (k == 11)
            a *= 9;
        let line = [
            i, ds(d), v, e, C[vi % 5], a, a > 10000 && r() < .8 ? 'M. Iyer' : a <= 10000 ? 'S. Rao' : ''
        ].join(',');
        if (k == 15 && last) {
            const q = last.split(',');
            q[0] = i;
            line = q.join(',');
        }
        last = line;
        o += '\n' + line;
    }
    return o;
}
async function load(text) {
    try {
        S.busy = 0;
        S.res = null;
        S.cache = {};
        S.err = '';
        for (let i = 0; i < STEPS.length; i++) {
            S.busy = i;
            draw();
            await sleep(320);
        }
        S.res = await api.analyze(text);
        S.busy = -1;
        S.sel = S.res.fl[0] || 0;
        S.pg = 'dash';
        draw();
    }
    catch (e) {
        S.busy = -1;
        S.err = e.message;
        draw();
    }
}
const pick = f => {
    if (f)
        f.text().then(load);
};
const pl = r => `<span class="pill ${r >= .7 ? 'hi' : r >= .45 ? 'me' : 'lo'}">${Math.round(r * 100)}</span>`;
const tb = (h, r) => `<div class="sc"><table><thead><tr>${h.map(x => `<th>${x}</th>`).join('')}</tr></thead><tbody>${r.join('')}</tbody></table></div>`;
const hd = (t, s) => `<h1>${t}</h1><p class="m">${s}</p>`;
const bar = (v, c) => `<div class="bar"><i style="width:${cl(v) * 100}%;background:${c}"></i></div>`;
const col = v => v >= .7 ? 'var(--g)' : v >= .45 ? 'var(--y)' : 'var(--r)';
const kp = (l, v, c) => `<div class="card"><div class="kl">${l}</div><div class="k" ${c ? `style="color:${c}"` : ''}>${v}</div></div>`;
const gauge = s => `<svg viewBox="0 0 160 160" width="190"><defs><linearGradient id="gr"><stop offset="0" stop-color="#7c5cff"/><stop offset="1" stop-color="#22d3ee"/></linearGradient></defs><circle cx="80" cy="80" r="64" fill="none" stroke="var(--p2)" stroke-width="14"/><circle cx="80" cy="80" r="64" fill="none" stroke="url(#gr)" stroke-width="14" stroke-linecap="round" stroke-dasharray="${402 * s / 100} 999" transform="rotate(-90 80 80)"/><text x="80" y="88" text-anchor="middle" fill="var(--t)" font-size="38" font-weight="800">${s}</text><text x="80" y="108" text-anchor="middle" fill="var(--m)" font-size="11">out of 100</text></svg>`;
const grade = s => s >= 85 ? 'A' : s >= 70 ? 'B' : s >= 55 ? 'C' : s >= 40 ? 'D' : 'E';
function flRows(R, n) {
    return R.fl.slice(0, n).map(i => {
        const r = R.rows[i];
        return `<tr><td>${esc(r.id)}</td><td>${r.d || '-'}</td><td>${esc(r.v)}</td><td>${esc(r.e)}</td><td>${fm(r.a)}</td><td>${pl(r.r)}</td><td>${r.ty}</td><td class="np"><button class="btn x" onclick="S.sel=${i};go('shap')">Explain</button></td></tr>`;
    });
}
function page() {
    const R = S.res;
    const p = S.pg;
    if (p == 'upload') {
        return hd('CSV Upload', 'Upload a financial ledger or expense CSV. Columns needed: amount. Optional: id, date, vendor, employee, category, approved_by.') + (S.busy >= 0 ? `<div class="card"><h2>Running AI audit pipeline…</h2>${STEPS.map((s, i) => `<div class="st ${i < S.busy ? 'd' : i == S.busy ? 'c' : ''}"><b>${i < S.busy ? '✓' : i + 1}</b>${s}</div>`).join('')}</div>` : `<div class="drop"><div style="font-size:42px">📂</div><h2>Drop your CSV here</h2><p class="m">Your CSV is analysed securely on the server and is not stored.</p><input id="f" type="file" accept=".csv,text/csv" style="display:none" onchange="pick(this.files[0])"><button class="btn" onclick="$('#f').click()">Choose CSV file</button> <button class="btn s" onclick="load(sample())">Try sample data</button>${S.err ? `<p style="color:var(--r)">${esc(S.err)}</p>` : ''}</div>`);
    }
    if (p == 'users') {
        const U = S.ul || {};
        return hd('User Management', 'Manage who can access the audit workspace.') + `<div class="card">${tb(['User', 'Role', 'Actions'], Object.entries(U).map(([n, u]) => `<tr><td>${esc(n)}</td><td>${S.u.role == 'Admin' && n != S.u.n ? `<select onchange="role('${esc(n)}',this.value)">${['Admin', 'Auditor', 'Viewer'].map(r => `<option ${r == u.role ? 'selected' : ''}>${r}</option>`).join('')}</select>` : u.role}</td><td>${S.u.role == 'Admin' && n != S.u.n ? `<button class="btn x s" onclick="delu('${esc(n)}')">Remove</button>` : '-'}</td></tr>`))}</div><p class="m">The first account created becomes Admin. Accounts are stored in this browser for the demo.</p>`;
    }
    if (!R)
        return hd(NAV.find(x => x[0] == p)[2], 'No dataset analysed yet.') + `<div class="card" style="text-align:center"><p>Upload a CSV to unlock this module.</p><button class="btn" onclick="go('upload')">Go to CSV Upload</button></div>`;
    if (p == 'clean') {
        const L = R.L;
        return hd('Data Cleaning', 'Automatic preprocessing and quality checks.') + `<div class="g">${kp('Raw rows', L.raw)}${kp('Valid rows', R.n, 'var(--g)')}${kp('Dropped (no amount)', L.miss, L.miss ? 'var(--y)' : '')}${kp('Negatives → absolute', L.neg)}${kp('Bad dates', L.dt)}${kp('Vendors filled', L.vn)}${kp('Employees filled', L.en)}${kp('Duplicates flagged', R.comp[2].f, R.comp[2].f ? 'var(--r)' : '')}</div><div class="card"><h2>Engineered features (first 8 rows, scaled 0–1)</h2>${tb(['#', ...FN], R.X.slice(0, 8).map((x, i) => `<tr><td>${i + 1}</td>${x.map(v => `<td>${v.toFixed(2)}</td>`).join('')}</tr>`))}</div>`;
    }
    if (p == 'fraud') {
        const mx = Math.max(...R.hist);
        return hd('Fraud Detection', 'VAE + GRU + Temporal Attention scoring. Flagged = top 5% risk.') + `<div class="g">${kp('Transactions', R.n)}${kp('Flagged', R.fl.length, 'var(--r)')}${kp('Exposure', fm(R.exp), 'var(--y)')}${kp('Value audited', fm(R.tot))}</div><div class="g2"><div class="card"><h2>Risk distribution</h2><div class="hist">${R.hist.map(h => `<i style="height:${h / mx * 100}%" title="${h}"></i>`).join('')}</div><div class="m" style="margin:6px 0 0">Low risk ← → High risk</div></div><div class="card"><h2>Temporal attention (weight on each step of the window)</h2>${R.A.map((a, i) => `<div style="display:grid;grid-template-columns:150px 1fr;gap:8px;font-size:12px"><span>${i == R.A.length - 1 ? 'Current transaction' : 't-' + (R.A.length - 1 - i)}</span>${bar(a * 5, 'var(--a)')}</div>`).join('')}</div></div><div class="card"><h2>Top flagged transactions</h2>${tb(['ID', 'Date', 'Vendor', 'Employee', 'Amount', 'Risk', 'Likely pattern', ''], flRows(R, 25))}</div>`;
    }
    if (p == 'shap' && !R.shap.length)
        return hd('SHAP Explainability', 'No flagged transactions to explain.');
    if (p == 'shap') {
        const i = S.sel;
        const s = R.shap[i];
        const r = R.rows[i];
        const o = s.phi.map((v, j) => j).sort((a, b) => Math.abs(s.phi[b]) - Math.abs(s.phi[a]));
        const mx = Math.max(...s.phi.map(Math.abs)) || 1;
        const t3 = o.slice(0, 3).filter(j => s.phi[j] > 0).map(j => FN[j].toLowerCase());
        if (!S.cache.g) {
            S.cache.g = Array(9).fill(0);
            R.shap.slice(0, 30).forEach(q => q.phi.forEach((v, j) => S.cache.g[j] += Math.abs(v) / Math.min(30, R.shap.length)));
        }
        const gm = Math.max(...S.cache.g) || 1;
        return hd('SHAP Explainability', 'SHAP values (KernelExplainer) show why a transaction was scored.') + `<div class="card"><select onchange="S.sel=+this.value;draw()">${R.fl.slice(0, 40).map(k => `<option value="${k}" ${k == i ? 'selected' : ''}>#${esc(R.rows[k].id)} · ${esc(R.rows[k].v)} · ${fm(R.rows[k].a)}</option>`).join('')}</select><p>Baseline risk <b>${Math.round(s.base * 100)}</b> → this transaction <b>${Math.round(s.out * 100)}</b> ${pl(s.out)}</p>${o.map(j => `<div class="wf"><span>${FN[j]}</span><div class="t"><i style="${s.phi[j] >= 0 ? `left:50%;width:${s.phi[j] / mx * 50}%;background:var(--r)` : `right:50%;width:${-s.phi[j] / mx * 50}%;background:var(--g)`}"></i></div><span>${s.phi[j] >= 0 ? '+' : ''}${(s.phi[j] * 100).toFixed(1)}</span></div>`).join('')}<div class="rc">${t3.length ? 'This payment of ' + fm(r.a) + ' to ' + esc(r.v) + ' is mainly driven up by: ' + t3.join(', ') + '.' : 'No single factor dominates this score.'} Red bars raise risk, green bars lower it.</div></div><div class="card" style="margin-top:14px"><h2>Global importance (top 30 flagged)</h2>${o.length ? S.cache.g.map((v, j) => `<div style="display:grid;grid-template-columns:170px 1fr;gap:8px;font-size:13px;margin:4px 0"><span>${FN[j]}</span>${bar(v / gm, 'var(--b)')}</div>`).join('') : ''}</div>`;
    }
    if (p == 'vendor') {
        return hd('Vendor Trust Score', 'Trust blends average risk, flagged-payment ratio and identity checks. Lower means riskier.') + `<div class="card">${tb(['Vendor', 'Payments', 'Value', 'Flagged', 'Trust', 'Rating'], R.vend.map(v => `<tr><td>${esc(v.name)}</td><td>${v.n}</td><td>${fm(v.tot)}</td><td>${v.fl}</td><td>${bar(v.sc / 100, col(v.sc / 100))}</td><td><span class="pill ${v.sc >= 70 ? 'lo' : v.sc >= 50 ? 'me' : 'hi'}">${v.sc} · ${v.sc >= 70 ? 'Trusted' : v.sc >= 50 ? 'Watch' : 'Risky'}</span></td></tr>`))}</div>`;
    }
    if (p == 'emp') {
        return hd('Employee Risk Assessment', 'Risk reflects the average and concentration of flagged transactions per employee.') + `<div class="g">${R.emp.slice(0, 4).map(e => kp(esc(e.name), e.sc, e.sc >= 60 ? 'var(--r)' : e.sc >= 35 ? 'var(--y)' : 'var(--g)')).join('')}</div><div class="card">${tb(['Employee', 'Transactions', 'Value', 'Flagged', 'Risk', 'Level'], R.emp.map(e => `<tr><td>${esc(e.name)}</td><td>${e.n}</td><td>${fm(e.tot)}</td><td>${e.fl}</td><td>${bar(e.sc / 100, col(1 - e.sc / 100))}</td><td><span class="pill ${e.sc >= 60 ? 'hi' : e.sc >= 35 ? 'me' : 'lo'}">${e.sc >= 60 ? 'High' : e.sc >= 35 ? 'Medium' : 'Low'}</span></td></tr>`))}</div>`;
    }
    if (p == 'comp') {
        return hd('Compliance Monitoring', 'Policy rules tested across every transaction.') + `<div class="g">${kp('Compliance score', Math.round(R.cs * 100) + '%', col(R.cs))}${kp('Rules breached', R.comp.filter(c => c.f).length)}${kp('Violations', R.comp.reduce((s, c) => s + c.f, 0), 'var(--y)')}</div><div class="card">${R.comp.map(c => `<div style="margin:12px 0"><div style="display:flex;justify-content:space-between"><span>${c.n}</span><b>${c.ok == null ? 'Not testable (no approver column)' : c.f + ' violations'}</b></div>${bar(c.ok == null ? 0 : c.ok, col(c.ok == null ? 0 : c.ok))}</div>`).join('')}</div>`;
    }
    if (p == 'health') {
        return hd('Financial Health Score', 'Composite of data quality, fraud exposure, compliance, vendor reliability and internal controls.') + `<div class="g2"><div class="card" style="text-align:center">${gauge(R.hs)}<h2>Grade ${grade(R.hs)}</h2></div><div class="card">${R.hc.map(([n, v]) => `<div style="margin:12px 0"><div style="display:flex;justify-content:space-between"><span>${n}</span><b>${Math.round(v * 100)}%</b></div>${bar(v, col(v))}</div>`).join('')}</div></div>`;
    }
    if (p == 'dash') {
        return `<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px"><div>${hd('Audit Dashboard', 'Smart Audit Analysis for Finance · ' + new Date().toLocaleDateString('en-IN', { dateStyle: 'long' }) + ' · ' + esc(S.u.n))}</div><div class="np"><button class="btn" onclick="api.pdf()">⬇ Download PDF report</button></div></div><div class="g">${kp('Financial health', R.hs + ' · ' + grade(R.hs), col(R.hs / 100))}${kp('Transactions', R.n)}${kp('Flagged fraud risks', R.fl.length, 'var(--r)')}${kp('Exposure', fm(R.exp), 'var(--y)')}${kp('Compliance', Math.round(R.cs * 100) + '%')}</div><div class="g2"><div class="card"><h2>Top flagged transactions</h2>${tb(['ID', 'Date', 'Vendor', 'Employee', 'Amount', 'Risk', 'Pattern', ''], flRows(R, 6))}</div><div class="card"><h2>Audit recommendations</h2>${R.recs.map(([l, t]) => `<div class="rc" style="border-color:${l == 'High' ? 'var(--r)' : l == 'Medium' ? 'var(--y)' : 'var(--g)'}"><b>${l}</b> · ${t}</div>`).join('')}</div></div><div class="g2"><div class="card"><h2>Riskiest vendors</h2>${tb(['Vendor', 'Trust'], R.vend.slice(0, 5).map(v => `<tr><td>${esc(v.name)}</td><td>${pl(1 - v.sc / 100)}</td></tr>`))}</div><div class="card"><h2>Highest-risk employees</h2>${tb(['Employee', 'Risk'], R.emp.slice(0, 5).map(e => `<tr><td>${esc(e.name)}</td><td>${pl(e.sc / 100)}</td></tr>`))}</div></div>`;
    }
}
function role(n, r) {
    const U = users();
    U[n].role = r;
    LS.s('sa_users', JSON.stringify(U));
}
function delu(n) {
    const U = users();
    delete U[n];
    LS.s('sa_users', JSON.stringify(U));
    draw();
}
function draw() {
    const a = $('#app');
    if (!S.u) {
        a.innerHTML = `<div class="auth"><div class="card"><div class="logo" style="font-size:26px;padding:0">SmartAudit AI</div><p class="m">AI-based financial anomaly detection, explainable risk and audit decisions.</p>${S.reg ? '<h2>Create account</h2>' : '<h2>Sign in</h2>'}<input id="un" placeholder="Username" autocomplete="username"><input id="pw" type="password" placeholder="Password" autocomplete="current-password" onkeydown="event.key=='Enter'&&auth()">${S.err ? `<p style="color:var(--r);margin:0 0 10px">${esc(S.err)}</p>` : ''}<button class="btn" style="width:100%" onclick="auth()">${S.reg ? 'Register' : 'Sign in'}</button><p class="m" style="text-align:center;margin:14px 0 0"><a href="#" style="color:var(--b)" onclick="S.reg=!S.reg;S.err='';draw();return false">${S.reg ? 'Have an account? Sign in' : 'New here? Create an account'}</a></p></div></div>`;
        return;
    }
    const sc = scrollY;
    a.innerHTML = `<aside class="side"><div class="logo">🛡️ SmartAudit AI</div>${NAV.filter(x => x[0] != 'users' || S.u.role == 'Admin').map(([k, i, n]) => `<button class="nv ${S.pg == k ? 'on' : ''}" onclick="go('${k}')">${i} ${n}</button>`).join('')}<button class="nv" onclick="api.logout()">🚪 Sign out (${esc(S.u.n)})</button></aside><main>${page()}</main>`;
    scrollTo(0, sc);
}
