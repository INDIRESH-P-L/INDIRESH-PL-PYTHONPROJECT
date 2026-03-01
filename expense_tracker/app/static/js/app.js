/* ═══════════════════════════════════════════════════
   Expense Tracker — Main Application JS
   ═══════════════════════════════════════════════════ */

// ── Category data ──────────────────────────────────────────────────────────────
const CATEGORIES = {
    income: [
        { value: 'Salary', label: '💼 Salary', color: '#0ea5e9' }, // Sky 500
        { value: 'Freelance', label: '🔧 Freelance', color: '#2dd4bf' }, // Teal 400
        { value: 'Investment', label: '📈 Investment', color: '#6366f1' }, // Indigo 500
        { value: 'Gift', label: '🎁 Gift', color: '#ec4899' }, // Pink 500
        { value: 'Rent Income', label: '🏠 Rent Income', color: '#10b981' }, // Emerald 500
        { value: 'Business', label: '🤝 Business', color: '#f59e0b' },
        { value: 'Bonus', label: '🏆 Bonus', color: '#fbbf24' },
        { value: 'Other', label: '💡 Other', color: '#64748b' }, // Slate 500
    ],
    expense: [
        { value: 'Groceries', label: '🛒 Groceries', color: '#f43f5e' }, // Rose 500
        { value: 'Food & Dining', label: '🍽️ Food & Dining', color: '#f97316' }, // Orange 500
        { value: 'Transport', label: '🚌 Transport', color: '#eab308' }, // Yellow 500
        { value: 'Rent', label: '🏠 Rent', color: '#6366f1' }, // Indigo 500
        { value: 'Utilities', label: '💡 Utilities', color: '#0ea5e9' }, // Sky 500
        { value: 'Health', label: '🏥 Health', color: '#10b981' }, // Emerald 500
        { value: 'Entertainment', label: '🎬 Entertainment', color: '#d946ef' }, // Fuchsia 500
        { value: 'Education', label: '📚 Education', color: '#8b5cf6' }, // Violet 500
        { value: 'Shopping', label: '👗 Shopping', color: '#f43f5e' }, // Rose 500
        { value: 'Travel', label: '✈️ Travel', color: '#06b6d4' }, // Cyan 500
        { value: 'EMI / Loan', label: '🏦 EMI / Loan', color: '#4f46e5' }, // Indigo 600
        { value: 'Subscriptions', label: '📺 Subscriptions', color: '#2dd4bf' }, // Teal 400
        { value: 'Other', label: '💡 Other', color: '#64748b' }, // Slate 500
    ],
};

const CAT_ICON = {};
const CAT_COLOR = {};
[...CATEGORIES.income, ...CATEGORIES.expense].forEach(c => {
    CAT_ICON[c.value] = c.label.split(' ')[0];
    CAT_COLOR[c.value] = c.color;
});

// ── State ──────────────────────────────────────────────────────────────────────
const state = {
    type: 'income',
    filter: 'all',
    month: '',
    search: '',
    transactions: [],
    summary: { income: 0, expense: 0, balance: 0, categories: [], trend: [] },
    limits: {},
};

// ── Chart instances ────────────────────────────────────────────────────────────
let donutChart = null;
let trendChart = null;

// ── DOM refs ───────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

// ── Init ───────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    setTodayDate();
    populateCats('income');
    await loadMonths();
    await refreshAll();
    bindEvents();
});

// ── Event wiring ───────────────────────────────────────────────────────────────
function bindEvents() {
    // Type toggle
    $('btn-income').addEventListener('click', () => switchType('income'));
    $('btn-expense').addEventListener('click', () => switchType('expense'));

    // Form submit
    $('tx-form').addEventListener('submit', handleSubmit);

    // Search
    $('tx-search').addEventListener('input', e => {
        state.search = e.target.value.toLowerCase();
        renderTxList();
    });

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            state.filter = btn.dataset.filter;
            document.querySelectorAll('.filter-btn').forEach(b => b.className = 'filter-btn');
            btn.classList.add(`active-${state.filter}`);
            renderTxList();
        });
    });

    // Month select
    $('month-select').addEventListener('change', async e => {
        state.month = e.target.value;
        await refreshAll();
    });

    // Close modal on click outside
    window.onclick = e => {
        if (e.target === $('limit-modal')) closeLimitModal();
    };
}

// ── Type switch ────────────────────────────────────────────────────────────────
function switchType(type) {
    state.type = type;
    $('tx-type-hidden').value = type;

    $('btn-income').className = 'type-btn' + (type === 'income' ? ' active-income' : '');
    $('btn-expense').className = 'type-btn' + (type === 'expense' ? ' active-expense' : '');

    populateCats(type);
}

function populateCats(type) {
    const sel = $('tx-category');
    sel.innerHTML = CATEGORIES[type]
        .map(c => `<option value="${c.value}">${c.label}</option>`)
        .join('');
}

// ── Today date ─────────────────────────────────────────────────────────────────
function setTodayDate() {
    const today = new Date().toISOString().slice(0, 10);
    $('tx-date').value = today;
}

// ── Load months dropdown ───────────────────────────────────────────────────────
async function loadMonths() {
    const months = await api('/api/months', {}, []);
    const sel = $('month-select');
    const opts = ['<option value="">All Time</option>'];
    months.forEach(m => {
        const [y, mo] = m.split('-');
        const label = new Date(parseInt(y, 10), parseInt(mo, 10) - 1)
            .toLocaleString('default', { month: 'long', year: 'numeric' });
        opts.push(`<option value="${m}">${label}</option>`);
    });
    sel.innerHTML = opts.join('');
}

// ── Refresh all data ───────────────────────────────────────────────────────────
async function refreshAll() {
    const [txs, summary, aiInsights, limits] = await Promise.all([
        api(`/api/transactions${state.month ? `?month=${state.month}` : ''}`, {}, []),
        api(`/api/summary${state.month ? `?month=${state.month}` : ''}`, {},
            { income: 0, expense: 0, balance: 0, categories: [], trend: [] }),
        api(`/api/ai_insights${state.month ? `?month=${state.month}` : ''}`, {}, { insight: "Unable to load AI insights.", source: "" }),
        api('/api/limits', {}, {}),
    ]);

    // Guard: ensure data shapes are correct before rendering
    state.transactions = Array.isArray(txs) ? txs : [];
    state.limits = limits || {};
    state.summary = {
        income: typeof summary.income === 'number' ? summary.income : 0,
        expense: typeof summary.expense === 'number' ? summary.expense : 0,
        balance: typeof summary.balance === 'number' ? summary.balance : 0,
        categories: Array.isArray(summary.categories) ? summary.categories : [],
        trend: Array.isArray(summary.trend) ? summary.trend : [],
    };

    // Reset animated counter baselines when month changes
    ['stat-balance', 'stat-income', 'stat-expense'].forEach(id => {
        const el = $(id);
        if (el) el.dataset.val = '0';
    });

    renderStats();
    renderTxList();
    renderDonut();
    renderTrend();
    renderCatBars();

    // AI insight update
    const insightEl = $('ai-insight-text');
    if (insightEl && aiInsights.insight) {
        // Highlighting warning logic (if 'Warning:' is in text, make it red-ish)
        let text = aiInsights.insight;
        if (text.includes('Warning:')) {
            text = text.replace('Warning:', '<strong style="color:var(--red)">Warning:</strong>');
            insightEl.style.color = "var(--text-primary)";
        } else if (text.includes('Great job!')) {
            text = text.replace('Great job!', '<strong style="color:var(--green)">Great job!</strong>');
            insightEl.style.color = "var(--text-secondary)";
        } else {
            insightEl.style.color = "var(--text-secondary)";
        }
        insightEl.innerHTML = text;
    }

    await loadMonths();
}

// ── Stat cards ─────────────────────────────────────────────────────────────────
function renderStats() {
    const { income, expense, balance } = state.summary;
    animateValue($('stat-balance'), balance);
    animateValue($('stat-income'), income);
    animateValue($('stat-expense'), expense);

    const balEl = $('stat-balance');
    balEl.className = 'stat-value ' + (balance >= 0 ? 'positive' : 'negative');
}

function animateValue(el, target) {
    const start = parseFloat(el.dataset.val || '0');
    const diff = target - start;
    const dur = 600;
    const t0 = performance.now();

    function step(now) {
        const p = Math.min((now - t0) / dur, 1);
        const v = start + diff * easeOut(p);
        el.textContent = fmt(v);
        if (p < 1) requestAnimationFrame(step);
        else { el.textContent = fmt(target); el.dataset.val = target; }
    }
    requestAnimationFrame(step);
}
function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

// ── Transaction list ───────────────────────────────────────────────────────────
function renderTxList() {
    const listEl = $('tx-list');
    const countEl = $('tx-count');

    let items = [...state.transactions];

    // Type filter
    if (state.filter !== 'all') items = items.filter(t => t.type === state.filter);

    // Search
    if (state.search) {
        items = items.filter(t =>
            t.category.toLowerCase().includes(state.search) ||
            (t.note || '').toLowerCase().includes(state.search)
        );
    }

    countEl.textContent = `${items.length} record${items.length !== 1 ? 's' : ''}`;

    if (items.length === 0) {
        listEl.innerHTML = `
      <div class="empty">
        <span class="empty-icon">🗂️</span>
        <p>${state.search ? 'No results found.' : 'No transactions yet.'}</p>
      </div>`;
        return;
    }

    listEl.innerHTML = items.map((tx, i) => `
    <div class="tx-item" id="tx-${tx.id}" style="animation-delay:${Math.min(i * 30, 200)}ms">
      <div class="tx-avatar ${tx.type}">${CAT_ICON[tx.category] || '💡'}</div>
      <div class="tx-body">
        <div class="tx-cat">${tx.category}</div>
        <div class="tx-note">${tx.note || '<span style="opacity:.4">No note</span>'}</div>
      </div>
      <div class="tx-right">
        <div class="tx-amount ${tx.type}">${tx.type === 'income' ? '+' : '-'}${fmt(tx.amount)}</div>
        <div class="tx-date">${fmtDate(tx.date)}</div>
      </div>
      <button class="btn-del" onclick="deleteTx(${tx.id})" title="Delete" aria-label="Delete record">🗑</button>
    </div>
  `).join('');
}

// ── Delete ─────────────────────────────────────────────────────────────────────
async function deleteTx(id) {
    const el = $(`tx-${id}`);
    if (el) { el.style.opacity = '.3'; el.style.pointerEvents = 'none'; }

    const ok = await api(`/api/transactions/${id}`, { method: 'DELETE' });
    if (ok.success) {
        toast('Record deleted', 'success');
        await refreshAll();
    } else {
        if (el) { el.style.opacity = '1'; el.style.pointerEvents = ''; }
        toast('Could not delete', 'error');
    }
}

// ── Form submit ────────────────────────────────────────────────────────────────
async function handleSubmit(e) {
    e.preventDefault();
    const btn = $('submit-btn');
    btn.disabled = true;
    btn.textContent = 'Adding…';

    const body = {
        type: $('tx-type-hidden').value,
        category: $('tx-category').value,
        amount: $('tx-amount').value,
        note: $('tx-note').value,
        date: $('tx-date').value,
    };

    const res = await api('/api/transactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });

    if (res.success) {
        if (res.warning) {
            toast(res.warning, 'error'); // Use error style for warnings
            // Also append to chatbot if it exists
            if (window.appendMessage) {
                window.appendMessage(res.warning, 'bot');
            }
        } else {
            toast('Transaction added!', 'success');
        }
        $('tx-amount').value = '';
        $('tx-note').value = '';
        state.month = '';
        $('month-select').value = '';
        await refreshAll();
    } else {
        toast(res.error || 'Something went wrong', 'error');
    }

    btn.disabled = false;
    btn.textContent = 'Add Transaction';
}

// ── Donut Chart ────────────────────────────────────────────────────────────────
function renderDonut() {
    const cats = state.summary.categories;
    const wrap = $('donut-section');

    if (!cats.length) {
        // Destroy old chart if present before clearing DOM
        if (donutChart) { donutChart.destroy(); donutChart = null; }
        wrap.innerHTML = `<div class="no-data"><span class="no-data-icon">🍩</span><p>No expense data yet</p></div>`;
        return;
    }

    wrap.innerHTML = `
    <div class="donut-wrap">
      <div class="donut-canvas-wrap">
        <canvas id="donut-chart" width="160" height="160"></canvas>
        <div class="donut-center">
          <span class="donut-center-pct" id="donut-label">100%</span>
          <span class="donut-center-label">Spent</span>
        </div>
      </div>
      <div class="legend" id="donut-legend"></div>
    </div>`;

    const total = cats.reduce((a, c) => a + c.total, 0);
    const top5 = cats.slice(0, 5);
    const rest = cats.slice(5).reduce((a, c) => a + c.total, 0);
    const data = rest > 0 ? [...top5, { category: 'Other', total: rest }] : top5;
    const colors = data.map(d => CAT_COLOR[d.category] || '#8b93b8');

    if (donutChart) donutChart.destroy();
    donutChart = new Chart($('donut-chart'), {
        type: 'doughnut',
        data: {
            labels: data.map(d => d.category),
            datasets: [{ data: data.map(d => d.total), backgroundColor: colors, borderWidth: 0, hoverOffset: 8 }],
        },
        options: {
            cutout: '68%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${fmt(ctx.raw)} (${((ctx.raw / total) * 100).toFixed(1)}%)`,
                    },
                },
            },
            onHover: (e, els) => {
                const labelEl = $('donut-label');
                if (!labelEl) return;
                if (els.length) {
                    const idx = els[0].index;
                    const pct = ((data[idx].total / total) * 100).toFixed(0);
                    labelEl.textContent = pct + '%';
                } else {
                    labelEl.textContent = '100%';
                }
            },
        },
    });

    // Legend
    $('donut-legend').innerHTML = data.map((d, i) => `
    <div class="legend-item">
      <span class="legend-dot" style="background:${colors[i]}"></span>
      <span class="legend-name">${d.category}</span>
      <span class="legend-val">${fmt(d.total)}</span>
    </div>`).join('');
}

// ── Trend Chart ────────────────────────────────────────────────────────────────
function renderTrend() {
    const trend = state.summary.trend;

    if (!trend.length) {
        // Destroy stale chart so canvas is clean for next render
        if (trendChart) { trendChart.destroy(); trendChart = null; }
        return;
    }

    const labels = trend.map(t => {
        const [y, m] = t.month.split('-');
        return new Date(y, m - 1).toLocaleString('default', { month: 'short' });
    });

    if (trendChart) trendChart.destroy();
    trendChart = new Chart($('trend-chart'), {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Income',
                    data: trend.map(t => t.income),
                    backgroundColor: 'rgba(6, 182, 212, 0.7)', // Cyan 500
                    borderRadius: 6,
                    borderSkipped: false,
                },
                {
                    label: 'Expense',
                    data: trend.map(t => t.expense),
                    backgroundColor: 'rgba(244, 63, 94, 0.7)', // Rose 500
                    borderRadius: 6,
                    borderSkipped: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#8b93b8', font: { family: 'Inter', size: 11 }, boxWidth: 10, padding: 14 },
                },
                tooltip: {
                    callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmt(ctx.raw)}` },
                },
            },
            scales: {
                x: { ticks: { color: '#64748b', font: { size: 11 } }, grid: { display: false } },
                y: {
                    ticks: { color: '#64748b', font: { size: 11 }, callback: v => fmtShort(v) },
                    grid: { color: 'rgba(15, 23, 42, 0.05)' },
                    border: { dash: [4, 4] },
                },
            },
        },
    });
}

// ── Category bars ──────────────────────────────────────────────────────────────
function renderCatBars() {
    const cats = state.summary.categories;
    const el = $('cat-bars');
    const wrap = $('cat-section');

    if (!cats.length) {
        wrap.style.display = 'none';
        return;
    }
    wrap.style.display = '';

    const max = cats[0].total;
    el.innerHTML = cats.slice(0, 10).map(c => {
        const limit = state.limits[c.category];
        const pct = limit ? (c.total / limit) * 100 : (c.total / max) * 100;
        const isOver = limit && c.total > limit;

        return `
        <div class="cat-row">
          <div class="cat-row-top">
            <span class="cat-row-name">
              ${CAT_ICON[c.category] || '💡'} ${c.category}
              ${limit ? `<span class="cat-row-limit">/ Limit: ${fmt(limit)}</span>` : ''}
            </span>
            <span class="cat-row-amt" style="color:${isOver ? 'var(--red)' : (CAT_COLOR[c.category] || '#ff4d6d')}">${fmt(c.total)}</span>
          </div>
          <div class="cat-track ${limit ? 'limit-set' : ''}" style="position:relative">
            <div class="cat-fill ${isOver ? 'over-limit' : ''}" 
                 style="width:${Math.min(pct, 100).toFixed(1)}%; background:${CAT_COLOR[c.category] || '#ff4d6d'}">
            </div>
            ${limit && pct < 100 ? `<div class="cat-marker" style="left:${Math.min(pct, 100).toFixed(1)}%"></div>` : ''}
          </div>
        </div>`;
    }).join('');
}

// ── Limit Modal ──────────────────────────────────────────────────────────────
function openLimitModal() {
    renderLimitList();
    $('limit-modal').classList.add('active');
}

function closeLimitModal() {
    $('limit-modal').classList.remove('active');
}

function renderLimitList() {
    const listEl = $('limit-list');
    listEl.innerHTML = CATEGORIES.expense.map(c => {
        const currentLimit = state.limits[c.value] || '';
        return `
        <div class="limit-item">
            <div class="limit-item-info">
                <span>${CAT_ICON[c.value]}</span>
                <span class="limit-item-cat">${c.value}</span>
            </div>
            <div style="display:flex; gap:10px; align-items:center;">
                <div class="limit-item-input-wrap">
                    <span>₹</span>
                    <input type="number" id="limit-input-${c.value}" value="${currentLimit}" placeholder="No limit" min="0" step="100">
                </div>
                <button class="btn-save-limit" onclick="saveLimit('${c.value}')">Set</button>
            </div>
        </div>`;
    }).join('');
}

async function saveLimit(category) {
    const val = $(`limit-input-${category}`).value;
    if (!val || parseFloat(val) <= 0) {
        toast('Please enter a valid limit', 'error');
        return;
    }

    const res = await api('/api/limits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, limit: val }),
    });

    if (res.success) {
        toast(`Limit set for ${category}`, 'success');
        await refreshAll();
        renderLimitList(); // Refresh modal list
    } else {
        toast(res.error || 'Failed to set limit', 'error');
    }
}

// ── Helpers ────────────────────────────────────────────────────────────────────
/**
 * Fetch JSON from the API.
 * @param {string} url
 * @param {RequestInit} opts
 * @param {*} fallback  Value returned on network error (defaults to {})
 */
async function api(url, opts = {}, fallback = {}) {
    try {
        const r = await fetch(url, opts);
        if (!r.ok && opts.method !== 'DELETE') {
            // Surface server errors so callers can show error toast
            return await r.json().catch(() => fallback);
        }
        return await r.json();
    } catch (err) {
        console.error('[API] fetch error:', url, err);
        return fallback;
    }
}

function fmt(n) {
    return '₹' + Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtShort(n) {
    if (n >= 1e6) return '₹' + (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return '₹' + (n / 1e3).toFixed(0) + 'K';
    return '₹' + n;
}

function fmtDate(d) {
    return new Date(d + 'T00:00:00').toLocaleDateString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric',
    });
}

let toastTimer;
function toast(msg, type = 'success') {
    const el = $('toast');
    const icon = type === 'success' ? '✅' : '❌';
    el.innerHTML = `${icon} ${msg}`;
    el.className = `show ${type}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.className = ''; }, 3200);
}
