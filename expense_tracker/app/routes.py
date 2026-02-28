from flask import Blueprint, request, jsonify, render_template, g
from datetime import datetime
from .models import (
    fetch_all_transactions,
    fetch_summary,
    insert_transaction,
    delete_transaction,
    fetch_available_months,
    check_category_limit_exceeded,
    set_limit,
    fetch_limits,
)
from .ai_agent import handle_chat, get_ai_insights

api = Blueprint("api", __name__, url_prefix="/api")

@api.before_request
def require_login():
    if g.user is None:
        return jsonify(error="Unauthorized"), 401

@api.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    if not message:
        return jsonify(error="Message is required"), 400
    
    reply = handle_chat(message)
    return jsonify(reply=reply)

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
    
    # — Check category limit —
    warning = None
    if tx_type == "expense":
        violation = check_category_limit_exceeded(category)
        if violation:
            warning = f"⚠️ Limit exceeded for {category}! Spent: ₹{violation['spent']}, Limit: ₹{violation['limit']}."

    return jsonify(success=True, warning=warning), 201


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

# ── Limits ────────────────────────────────────────────────────────────────────

@api.get("/limits")
def get_api_limits():
    return jsonify(fetch_limits())


@api.post("/limits")
def set_api_limit():
    data = request.get_json(silent=True) or {}
    category = data.get("category")
    try:
        limit = float(data.get("limit", 0))
        if limit <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(error="Limit must be a positive number"), 400

    if not category:
        return jsonify(error="Category is required"), 400

    set_limit(category, limit)
    return jsonify(success=True)
