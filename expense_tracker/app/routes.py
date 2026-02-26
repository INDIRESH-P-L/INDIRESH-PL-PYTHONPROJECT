from flask import Blueprint, request, jsonify, render_template
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'expenses.db')
expense_limits = {}

chatbot = Blueprint("chatbot", __name__)

@chatbot.route('/chatbot', methods=['POST'])
def chatbot_route():
    data = request.get_json()
    msg = data.get('message', '').lower()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    reply = ""
    if 'set limit' in msg:
        parts = msg.split()
        if len(parts) >= 4:
            category = parts[2]
            try:
                limit = float(parts[3])
                expense_limits[category] = limit
                reply = f"Limit for {category} set to {limit}."
            except ValueError:
                reply = "Please provide a valid number for limit."
        else:
            reply = "Usage: set limit <category> <amount>"
    elif 'analytics' in msg or 'summary' in msg:
        rows = conn.execute('SELECT category, SUM(amount) as total FROM transactions WHERE type="expense" GROUP BY category').fetchall()
        reply = "Expense Analytics:\n"
        for r in rows:
            reply += f"{r['category']}: {r['total']}\n"
    elif 'warn' in msg or 'check' in msg:
        rows = conn.execute('SELECT category, SUM(amount) as total FROM transactions WHERE type="expense" GROUP BY category').fetchall()
        warnings = []
        for r in rows:
            cat = r['category']
            total = r['total']
            limit = expense_limits.get(cat)
            if limit and total > limit:
                warnings.append(f"Warning: {cat} exceeded limit ({total}>{limit})!")
        reply = '\n'.join(warnings) if warnings else "No limits exceeded."
    else:
        reply = "Ask for analytics, set limits, or check warnings."
    conn.close()
    return jsonify({'reply': reply})
from flask import Blueprint, jsonify, request
from datetime import datetime
from .models import (
    fetch_all_transactions,
    fetch_summary,
    insert_transaction,
    delete_transaction,
    fetch_available_months,
)

api = Blueprint("api", __name__, url_prefix="/api")

@api.before_request
def require_login():
    from flask import g, jsonify
    if g.user is None:
        return jsonify(error="Unauthorized"), 401

# ── Transactions ───────────────────────────────────────────────────────────────

@api.get("/transactions")
def get_transactions():
    tx_type = request.args.get("type")
    month   = request.args.get("month")
    limit   = request.args.get("limit", type=int)
    return jsonify(fetch_all_transactions(limit=limit, tx_type=tx_type, month=month))


@api.post("/transactions")
def add_transaction():
    data = request.get_json(silent=True) or {}

    tx_type  = str(data.get("type",     "")).strip()
    category = str(data.get("category", "")).strip()
    note     = str(data.get("note",     "")).strip()
    date     = str(data.get("date",     "")).strip() or datetime.now().strftime("%Y-%m-%d")

    # — Validate —
    if tx_type not in ("income", "expense"):
        return jsonify(error="Type must be 'income' or 'expense'"), 400
    if not category:
        return jsonify(error="Category is required"), 400
    try:
        amount = float(data.get("amount", 0))
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(error="Amount must be a positive number"), 400

    # — Check if expense will exceed balance —
    if tx_type == "expense":
        summary = fetch_summary()
        new_balance = summary["balance"] - amount
        if new_balance < 0:
            return jsonify(error=f"Insufficient balance. Current balance: {summary['balance']:.2f}, Expense amount: {amount:.2f}"), 400

    insert_transaction(tx_type, category, amount, note, date)
    return jsonify(success=True), 201


@api.delete("/transactions/<int:tx_id>")
def remove_transaction(tx_id):
    delete_transaction(tx_id)
    return jsonify(success=True)


# ── Summary ────────────────────────────────────────────────────────────────────

@api.get("/summary")
def get_summary():
    month = request.args.get("month")
    return jsonify(fetch_summary(month=month))

# ── AI Insights ────────────────────────────────────────────────────────────────

@api.get("/ai_insights")
def ai_insights():
    month = request.args.get("month")
    from .ai_agent import get_ai_insights
    return jsonify(get_ai_insights(month=month))

# ── Meta ───────────────────────────────────────────────────────────────────────

@api.get("/months")
def get_months():
    return jsonify(fetch_available_months())
