from flask import Blueprint, request, jsonify, render_template, g
from datetime import datetime
from .extensions import db
from sqlalchemy import func, case, desc
from .models import (
    fetch_all_transactions,
    fetch_summary,
    insert_transaction,
    delete_transaction,
    fetch_available_months,
    check_category_limit_exceeded,
    set_limit,
    fetch_limits,
    get_detailed_analytics,
    get_expense_warnings,
)
from .ai_agent import handle_chat, get_ai_insights
from app import limiter, csrf
import re

api = Blueprint("api", __name__, url_prefix="/api")

# Valid category whitelist — MUST stay in sync with frontend CATEGORIES
VALID_CATEGORIES = [
    # Income
    'Salary', 'Freelance', 'Investment', 'Gift', 'Rent Income', 'Business', 'Bonus', 'Other Income',
    # Expense
    'Groceries', 'Food & Dining', 'Transport', 'Rent', 'Utilities',
    'Health', 'Entertainment', 'Education', 'Shopping', 'Travel',
    'EMI / Loan', 'Subscriptions', 'Other'
]

def validate_date_format(date_str):
    """Validate date is in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

@api.before_request
def require_login():
    if g.user is None:
        return jsonify(error="Unauthorized"), 401

@api.post("/chat")
@csrf.exempt
@limiter.limit("20 per minute")
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    if not message:
        return jsonify(error="Message is required"), 400
    if len(message) > 2000:
        return jsonify(error="Message must be 2000 characters or less"), 400

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
@csrf.exempt
@limiter.limit("30 per minute")
def add_transaction():
    data = request.get_json(silent=True) or {}

    tx_type  = str(data.get("type",     "")).strip()
    category = str(data.get("category", "")).strip()
    note     = str(data.get("note",     "")).strip()
    date     = str(data.get("date",     "")).strip() or datetime.now().strftime("%Y-%m-%d")

    # — Validate type —
    if tx_type not in ("income", "expense"):
        return jsonify(error="Type must be 'income' or 'expense'"), 400

    # — Validate category —
    if not category:
        return jsonify(error="Category is required"), 400
    if category not in VALID_CATEGORIES:
        return jsonify(error=f"Invalid category. Valid categories: {', '.join(VALID_CATEGORIES)}"), 400

    # — Validate amount —
    try:
        amount = float(data.get("amount", 0))
        if amount <= 0:
            raise ValueError
        if amount > 10000000:  # 10 million max
            return jsonify(error="Amount exceeds maximum allowed value"), 400
    except (TypeError, ValueError):
        return jsonify(error="Amount must be a positive number"), 400

    # — Validate date —
    if not validate_date_format(date):
        return jsonify(error="Invalid date format. Use YYYY-MM-DD"), 400

    # — Validate note length —
    if len(note) > 500:
        return jsonify(error="Note must be 500 characters or less"), 400

    insert_transaction(tx_type, category, amount, note, date)

    # — Check category limit —
    warning = None
    if tx_type == "expense":
        violation = check_category_limit_exceeded(category)
        if violation:
            warning = f"Limit exceeded for {category}! Spent: {violation['spent']}, Limit: {violation['limit']}."

    return jsonify(success=True, warning=warning), 201


@api.delete("/transactions/<int:tx_id>")
@csrf.exempt
@limiter.limit("30 per minute")
def remove_transaction(tx_id):
    delete_transaction(tx_id)
    return jsonify(success=True)


# ── Summary ────────────────────────────────────────────────────────────────────

@api.get("/summary")
def get_summary():
    month = request.args.get("month")
    return jsonify(fetch_summary(month=month))

# ── User Profile ─────────────────────────────────────────────────────────────

@api.get("/user/profile")
def get_profile():
    from .models import User
    user_id = g.user["id"]
    user = User.query.get(user_id)
    if not user:
        return jsonify(error="User not found"), 404
        
    return jsonify({
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name or "",
        "bio": user.bio or "",
        "phone": user.phone or "",
        "avatar_url": user.avatar_url or "",
        "currency": user.currency or "INR",
        "created_at": (user.created_at.strftime("%Y-%m-%d") if isinstance(user.created_at, datetime) else str(user.created_at)[:10]) if user.created_at else ""
    })

@api.post("/user/profile")
@csrf.exempt
@limiter.limit("10 per minute")
def update_profile():
    from .models import User
    data = request.get_json(silent=True) or {}
    user_id = g.user["id"]
    user = User.query.get(user_id)
    
    if not user:
        return jsonify(error="User not found"), 404
        
    user.full_name = data.get("full_name", user.full_name)
    user.bio = data.get("bio", user.bio)
    user.phone = data.get("phone", user.phone)
    user.avatar_url = data.get("avatar_url", user.avatar_url)
    user.currency = data.get("currency", user.currency)
    
    db.session.commit()
    return jsonify(success=True)

# ── Export ───────────────────────────────────────────────────────────────────

@api.get("/export")
def export_csv():
    import csv
    import io
    from flask import Response
    from .models import Transaction
    
    user_id = g.user["id"]
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Note'])
    
    for tx in transactions:
        writer.writerow([tx.date, tx.type, tx.category, tx.amount, tx.note])
    
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=transactions.csv"
    return response

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
@csrf.exempt
@limiter.limit("20 per minute")
def set_api_limit():
    data = request.get_json(silent=True) or {}
    category = data.get("category")
    try:
        limit = float(data.get("limit", 0))
        if limit <= 0:
            raise ValueError
        if limit > 10000000:  # 10 million max
            return jsonify(error="Limit exceeds maximum allowed value"), 400
    except (TypeError, ValueError):
        return jsonify(error="Limit must be a positive number"), 400

    if not category:
        return jsonify(error="Category is required"), 400
    if category not in VALID_CATEGORIES:
        return jsonify(error=f"Invalid category. Valid categories: {', '.join(VALID_CATEGORIES)}"), 400

    set_limit(category, limit)
    return jsonify(success=True)


# ── Analytics ──────────────────────────────────────────────────────────────────

@api.get("/analytics/detailed")
def get_detailed_analytics_api():
    """Get comprehensive spending analytics with daily/weekly breakdown."""
    month = request.args.get("month")
    try:
        analytics = get_detailed_analytics(month=month)
        return jsonify(analytics)
    except Exception as e:
        print(f"Analytics error: {e}")
        return jsonify(error=str(e)), 500


@api.get("/analytics/warnings")
def get_warnings_api():
    """Get all active expense warnings and alerts."""
    try:
        warnings = get_expense_warnings()
        return jsonify(warnings=warnings)
    except Exception as e:
        print(f"Warnings error: {e}")
        return jsonify(error=str(e)), 500


# ── Expense Timeline (Daily aggregation) ────────────────────────────────────────

@api.get("/expenses/daily")
def get_daily_expenses():
    """
    Returns per-day income/expense aggregates for the timeline graph.
    Optional query params:
      - from  (YYYY-MM-DD) : start date inclusive
      - to    (YYYY-MM-DD) : end date inclusive
    """
    from .models import Transaction
    from flask import g

    user_id = g.user["id"]
    from_date = request.args.get("from", "")
    to_date   = request.args.get("to", "")

    query = db.session.query(Transaction).filter_by(user_id=user_id)

    if from_date:
        query = query.filter(Transaction.date >= from_date)
    if to_date:
        query = query.filter(Transaction.date <= to_date)

    transactions = query.order_by(Transaction.date.asc()).all()

    from datetime import datetime, timedelta

    # Aggregate per day using Python
    day_map = {}

    # Pre-populate day_map with the entire date range to avoid missing days
    if from_date and to_date:
        try:
            start_dt = datetime.strptime(from_date, "%Y-%m-%d")
            end_dt = datetime.strptime(to_date, "%Y-%m-%d")
            curr_dt = start_dt
            while curr_dt <= end_dt:
                d_str = curr_dt.strftime("%Y-%m-%d")
                day_map[d_str] = {"date": d_str, "income": 0.0, "expense": 0.0}
                curr_dt += timedelta(days=1)
        except ValueError:
            pass

    for tx in transactions:
        # the format is YYYY-MM-DD
        d = tx.date[:10]
        if d not in day_map:
            day_map[d] = {"date": d, "income": 0.0, "expense": 0.0}
        
        if tx.type == "income":
            day_map[d]["income"] += tx.amount
        else:
            day_map[d]["expense"] += tx.amount

    result = sorted(day_map.values(), key=lambda x: x["date"])
    for row in result:
        row["net"] = round(row["income"] - row["expense"], 2)
        row["income"]  = round(row["income"], 2)
        row["expense"] = round(row["expense"], 2)

    return jsonify(result)


@api.get("/user/created_at")
def get_user_created_at():
    """Returns the date of the user's first transaction as the account creation date."""
    from .models import Transaction
    from flask import g
    from datetime import datetime

    user_id = g.user["id"]
    earliest_tx = db.session.query(Transaction.date).filter_by(user_id=user_id).order_by(Transaction.date.asc()).first()
    
    if earliest_tx and earliest_tx.date:
        return jsonify(created_at=earliest_tx.date[:10])
    
    return jsonify(created_at=datetime.now().strftime("%Y-%m-%d"))

