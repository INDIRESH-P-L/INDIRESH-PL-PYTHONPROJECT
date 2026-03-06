from .database import get_db
from flask import g
from datetime import datetime, timedelta


# ── Query helpers ──────────────────────────────────────────────────────────────

def fetch_all_transactions(limit=None, tx_type=None, month=None):
    db = get_db()
    user_id = g.user["id"]
    sql    = "SELECT * FROM transactions WHERE user_id = ?"
    params = [user_id]

    if tx_type in ("income", "expense"):
        sql += " AND type = ?"
        params.append(tx_type)

    if month:                      # e.g. "2026-02"
        sql += " AND strftime('%Y-%m', date) = ?"
        params.append(month)

    sql += " ORDER BY date DESC, id DESC"

    if limit:
        sql += " LIMIT ?"
        params.append(limit)

    return [dict(r) for r in db.execute(sql, params).fetchall()]


def fetch_summary(month=None):
    db     = get_db()
    user_id = g.user["id"]
    params = [user_id]
    where  = "AND user_id = ?"

    if month:
        where += " AND strftime('%Y-%m', date) = ?"
        params.append(month)

    income  = db.execute(
        f"SELECT COALESCE(SUM(amount), 0) AS t FROM transactions WHERE type='income' {where}",
        params
    ).fetchone()["t"]

    expense = db.execute(
        f"SELECT COALESCE(SUM(amount), 0) AS t FROM transactions WHERE type='expense' {where}",
        params
    ).fetchone()["t"]

    # Category breakdown (expense only)
    cat_rows = db.execute(
        f"""SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE type='expense' {where}
            GROUP BY category
            ORDER BY total DESC""",
        params
    ).fetchall()

    # Monthly trend (last 6 months)
    trend = db.execute("""
        SELECT
            strftime('%Y-%m', date) AS month,
            SUM(CASE WHEN type='income'  THEN amount ELSE 0 END) AS income,
            SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expense
        FROM transactions
        WHERE user_id = ?
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    """, (user_id,)).fetchall()

    return {
        "income":     income,
        "expense":    expense,
        "balance":    income - expense,
        "categories": [dict(r) for r in cat_rows],
        "trend":      [dict(r) for r in reversed(trend)],
    }


def insert_transaction(tx_type, category, amount, note, date):
    db = get_db()
    user_id = g.user["id"]
    db.execute(
        "INSERT INTO transactions (user_id, type, category, amount, note, date) VALUES (?,?,?,?,?,?)",
        (user_id, tx_type, category, amount, note, date),
    )
    db.commit()


def delete_transaction(tx_id):
    db = get_db()
    user_id = g.user["id"]
    db.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id))
    db.commit()


def fetch_available_months():
    db = get_db()
    user_id = g.user["id"]
    rows = db.execute(
        "SELECT DISTINCT strftime('%Y-%m', date) AS m FROM transactions WHERE user_id = ? ORDER BY m DESC", (user_id,)
    ).fetchall()
    return [r["m"] for r in rows]


def set_limit(category, limit):
    db = get_db()
    user_id = g.user["id"]
    db.execute(
        """INSERT INTO limits (user_id, category, monthly_limit) VALUES (?, ?, ?)
           ON CONFLICT(user_id, category) DO UPDATE SET monthly_limit=excluded.monthly_limit""",
        (user_id, category, limit)
    )
    db.commit()


def fetch_limits():
    db = get_db()
    user_id = g.user["id"]
    rows = db.execute("SELECT category, monthly_limit FROM limits WHERE user_id = ?", (user_id,)).fetchall()
    return {r["category"]: r["monthly_limit"] for r in rows}


def check_category_limit_exceeded(category, month=None):
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    db = get_db()
    user_id = g.user["id"]
    
    # Get limit
    limit_row = db.execute(
        "SELECT monthly_limit FROM limits WHERE user_id = ? AND category = ?", 
        (user_id, category)
    ).fetchone()
    
    if not limit_row:
        return None  # No limit set
    
    limit = limit_row["monthly_limit"]
    
    # Get total spent this month in this category
    spent_row = db.execute(
        """SELECT COALESCE(SUM(amount), 0) as total 
           FROM transactions 
           WHERE user_id = ? AND category = ? AND type = 'expense' AND strftime('%Y-%m', date) = ?""",
        (user_id, category, month)
    ).fetchone()
    
    total_spent = spent_row["total"]
    
    if total_spent > limit:
        return {"category": category, "limit": limit, "spent": total_spent, "exceeded_by": total_spent - limit}
    
    return None


def store_ai_memory(key, content):
    db = get_db()
    user_id = g.user["id"]
    db.execute(
        "INSERT OR REPLACE INTO ai_memory (user_id, key, content) VALUES (?, ?, ?)",
        (user_id, key, content)
    )
    db.commit()


def fetch_ai_memory(key=None):
    db = get_db()
    user_id = g.user["id"]
    sql = "SELECT key, content FROM ai_memory WHERE user_id = ?"
    params = [user_id]
    if key:
        sql += " AND key = ?"
        params.append(key)
    
    rows = db.execute(sql, params).fetchall()
    if key:
        return [r["content"] for r in rows]
    
    result = {}
    for r in rows:
        if r["key"] not in result:
            result[r["key"]] = []
        result[r["key"]].append(r["content"])
    return result


# ── Advanced Analytics ─────────────────────────────────────────────────────────

def get_detailed_analytics(month=None):
    """Get comprehensive spending analytics with warnings and insights."""
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    db = get_db()
    user_id = g.user["id"]
    
    # Current month summary
    summary = fetch_summary(month)
    
    # Daily breakdown
    daily_rows = db.execute("""
        SELECT 
            date,
            SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as expense
        FROM transactions
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        GROUP BY date
        ORDER BY date
    """, (user_id, month)).fetchall()
    
    daily_breakdown = [dict(r) for r in daily_rows]
    
    # Weekly breakdown
    weekly_rows = db.execute("""
        SELECT 
            strftime('%W', date) as week,
            SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as expense
        FROM transactions
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        GROUP BY week
        ORDER BY week
    """, (user_id, month)).fetchall()
    
    weekly_breakdown = [dict(r) for r in weekly_rows]
    
    # Check all limits
    limits = fetch_limits()
    limit_status = []
    
    for category, limit in limits.items():
        spent_row = db.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM transactions 
            WHERE user_id = ? AND category = ? AND type = 'expense' AND strftime('%Y-%m', date) = ?
        """, (user_id, category, month)).fetchone()
        
        spent = spent_row["total"]
        status = "normal"
        if spent > limit:
            status = "exceeded"
        elif spent > limit * 0.9:
            status = "critical"
        elif spent > limit * 0.7:
            status = "warning"
        
        limit_status.append({
            "category": category,
            "limit": limit,
            "spent": spent,
            "remaining": max(0, limit - spent),
            "percentage": (spent / limit * 100) if limit > 0 else 0,
            "status": status
        })
    
    # Sort by spending
    limit_status.sort(key=lambda x: x["spent"], reverse=True)
    
    # Spending velocity (daily average)
    days_elapsed = len(daily_breakdown)
    daily_avg_expense = summary["expense"] / days_elapsed if days_elapsed > 0 else 0
    
    # Prediction for month-end
    total_days_in_month = (datetime(datetime.now().year if month.startswith(datetime.now().strftime("%Y")) else int(month.split('-')[0]), 
                                   int(month.split('-')[1]), 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    total_days = total_days_in_month.day
    
    projected_expense = daily_avg_expense * total_days if daily_avg_expense > 0 else 0
    
    return {
        "summary": summary,
        "daily_breakdown": daily_breakdown,
        "weekly_breakdown": weekly_breakdown,
        "limit_status": limit_status,
        "spending_velocity": {
            "daily_average": daily_avg_expense,
            "days_elapsed": days_elapsed,
            "total_days_in_month": total_days,
            "projected_expense": projected_expense,
            "on_track": projected_expense <= summary["income"] if summary["income"] > 0 else True
        }
    }


def get_expense_warnings():
    """Get all active expense warnings for the user."""
    month = datetime.now().strftime("%Y-%m")
    db = get_db()
    user_id = g.user["id"]
    
    warnings = []
    limits = fetch_limits()
    summary = fetch_summary(month)
    
    # Check each limit
    for category, limit in limits.items():
        spent_row = db.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM transactions 
            WHERE user_id = ? AND category = ? AND type = 'expense' AND strftime('%Y-%m', date) = ?
        """, (user_id, category, month)).fetchone()
        
        spent = spent_row["total"]
        
        if spent > limit:
            warnings.append({
                "type": "exceeded",
                "category": category,
                "limit": limit,
                "spent": spent,
                "exceeded_by": spent - limit,
                "message": f"⚠️ CRITICAL: {category} limit exceeded! Spent ₹{spent:.2f} of ₹{limit:.2f} limit (₹{spent-limit:.2f} over)"
            })
        elif spent > limit * 0.9:
            warnings.append({
                "type": "critical",
                "category": category,
                "limit": limit,
                "spent": spent,
                "remaining": limit - spent,
                "message": f"🔴 CRITICAL: {category} at 90%+! Spent ₹{spent:.2f} of ₹{limit:.2f} (₹{limit-spent:.2f} remaining)"
            })
        elif spent > limit * 0.75:
            warnings.append({
                "type": "warning",
                "category": category,
                "limit": limit,
                "spent": spent,
                "remaining": limit - spent,
                "message": f"🟡 WARNING: {category} at 75%! Spent ₹{spent:.2f} of ₹{limit:.2f} (₹{limit-spent:.2f} remaining)"
            })
    
    # Overall balance warning
    if summary["balance"] < 0:
        warnings.insert(0, {
            "type": "critical",
            "category": "Overall",
            "message": f"🔴 CRITICAL: Negative balance! You're ₹{abs(summary['balance']):.2f} in deficit.",
            "balance": summary["balance"]
        })
    elif summary["balance"] < summary["income"] * 0.1:
        warnings.insert(0, {
            "type": "warning",
            "category": "Overall",
            "message": f"🟡 WARNING: Low balance warning! Balance is only ₹{summary['balance']:.2f}",
            "balance": summary["balance"]
        })
    
    return warnings
