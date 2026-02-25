from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'expenses.db')

# ─── Database Setup ────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            type      TEXT    NOT NULL CHECK(type IN ('income','expense')),
            category  TEXT    NOT NULL,
            amount    REAL    NOT NULL,
            note      TEXT,
            date      TEXT    NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM transactions ORDER BY date DESC, id DESC'
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/summary', methods=['GET'])
def get_summary():
    conn = get_db()
    income  = conn.execute("SELECT COALESCE(SUM(amount),0) as t FROM transactions WHERE type='income'").fetchone()['t']
    expense = conn.execute("SELECT COALESCE(SUM(amount),0) as t FROM transactions WHERE type='expense'").fetchone()['t']
    balance = income - expense

    # Category breakdown for expenses
    cat_rows = conn.execute(
        "SELECT category, SUM(amount) as total FROM transactions WHERE type='expense' GROUP BY category ORDER BY total DESC"
    ).fetchall()
    conn.close()

    return jsonify({
        'income': income,
        'expense': expense,
        'balance': balance,
        'categories': [dict(r) for r in cat_rows]
    })

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    data = request.get_json()
    tx_type   = data.get('type', '').strip()
    category  = data.get('category', '').strip()
    amount    = data.get('amount')
    note      = data.get('note', '').strip()
    date      = data.get('date') or datetime.now().strftime('%Y-%m-%d')

    if tx_type not in ('income', 'expense'):
        return jsonify({'error': 'Invalid type'}), 400
    if not category:
        return jsonify({'error': 'Category required'}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({'error': 'Amount must be a positive number'}), 400

    conn = get_db()

    if tx_type == 'expense':
        income = conn.execute("SELECT COALESCE(SUM(amount),0) as t FROM transactions WHERE type='income'").fetchone()['t']
        expense = conn.execute("SELECT COALESCE(SUM(amount),0) as t FROM transactions WHERE type='expense'").fetchone()['t']
        if expense + amount > income:
            conn.close()
            return jsonify({'error': 'Expense cannot exceed total income'}), 400

    conn.execute(
        'INSERT INTO transactions (type, category, amount, note, date) VALUES (?,?,?,?,?)',
        (tx_type, category, amount, note, date)
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True}), 201

@app.route('/api/transactions/<int:tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    conn = get_db()
    conn.execute('DELETE FROM transactions WHERE id = ?', (tx_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print("\n  [Expense Tracker]  Running at  http://127.0.0.1:5000\n")
    from waitress import serve
    serve(app, host='127.0.0.1', port=5000)
