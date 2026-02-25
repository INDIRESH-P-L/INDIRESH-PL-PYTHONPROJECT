from .database import get_db
from flask import g


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
