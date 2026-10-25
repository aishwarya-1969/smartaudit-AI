/* API client + authentication wiring (loaded after app.js, overrides its local-only auth helpers). */
const TK = 'sa_token';
const api = {
    tok: () => LS.g(TK),
    async req(path, opt = {}) {
        const h = { ...(opt.headers || {}) };
        if (api.tok())
            h.Authorization = 'Bearer ' + api.tok();
        const r = await fetch('/api' + path, {
            ...opt, headers: h
        });
        if (r.status == 401 && S.u) {
            api.logout();
            throw new Error('Session expired. Please sign in again.');
        }
        if (!r.ok) {
            let m = 'Request failed (' + r.status + ')';
            try {
                const d = (await r.json()).detail;
                if (typeof d == 'string')
                    m = d;
            }
            catch (e) {
            }
            throw new Error(m);
        }
        return r;
    },
    async json(path, method, body) {
        return (await api.req(path, {
            method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
        })).json();
    },
    async analyze(text) {
        const fd = new FormData();
        fd.append('file', new Blob([text], { type: 'text/csv' }), 'data.csv');
        return (await api.req('/analyze', {
            method: 'POST', body: fd
        })).json();
    },
    async pdf() {
        try {
            const b = await (await api.req('/report')).blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(b);
            a.download = 'smartaudit-report.pdf';
            a.click();
        }
        catch (e) {
            alert(e.message);
        }
    },
    async users() {
        try {
            S.ul = Object.fromEntries((await (await api.req('/auth/users')).json()).map(u => [u.name, { role: u.role }]));
        }
        catch (e) {
            S.ul = {};
        }
    },
    logout() {
        LS.s(TK, '');
        S.u = null;
        S.res = null;
        S.pg = 'upload';
        draw();
    }
};
async function auth() {
    const n = $('#un').value.trim().toLowerCase();
    const p = $('#pw').value;
    if (n.length < 2 || p.length < 4) {
        S.err = 'Enter a username and a password of 4+ characters';
        return draw();
    }
    try {
        const d = await api.json('/auth/' + (S.reg ? 'register' : 'login'), 'POST', {
            username: n, password: p
        });
        LS.s(TK, d.token);
        S.u = {
            n: d.user.name, role: d.user.role
        };
        S.err = '';
        S.pg = 'upload';
    }
    catch (e) {
        S.err = e.message;
    }
    draw();
}
async function role(n, r) {
    try {
        await api.json('/auth/users/' + encodeURIComponent(n), 'PATCH', { role: r });
    }
    catch (e) {
        alert(e.message);
    }
}
async function delu(n) {
    try {
        await api.req('/auth/users/' + encodeURIComponent(n), { method: 'DELETE' });
        await api.users();
    }
    catch (e) {
        alert(e.message);
    }
    draw();
}
(async () => {
    if (api.tok()) {
        try {
            const u = await (await api.req('/auth/me')).json();
            S.u = {
                n: u.name, role: u.role
            };
        }
        catch (e) {
            LS.s(TK, '');
        }
    }
    draw();
})();
