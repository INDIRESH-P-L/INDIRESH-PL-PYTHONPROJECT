from datetime import datetime
from .extensions import db
from flask import g

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200))
    google_id = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(120), unique=True)
    
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    limits = db.relationship('Limit', backref='user', lazy=True)
    memories = db.relationship('AIMemory', backref='user', lazy=True)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(10), nullable=False) # 'income' or 'expense'
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.Text, default='')
    date = db.Column(db.String(20), nullable=False) # Stored as string for now to match current logic

class Limit(db.Model):
    __tablename__ = 'limits'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    monthly_limit = db.Column(db.Float, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'category', name='_user_category_uc'),)

class AIMemory(db.Model):
    __tablename__ = 'ai_memory'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    key = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'key', 'content', name='_user_key_content_uc'),)

# ── helper functions (converted to ORM) ──────────────────────────────────────────────

def fetch_all_transactions(limit=None, tx_type=None, month=None):
    user_id = g.user["id"]
    query = Transaction.query.filter_by(user_id=user_id)

    if tx_type in ("income", "expense"):
        query = query.filter_by(type=tx_type)

    if month: # e.g. "2026-02"
        query = query.filter(Transaction.date.like(f"{month}%"))

    query = query.order_by(Transaction.date.desc(), Transaction.id.desc())

    if limit:
        query = query.limit(limit)

    results = query.all()
    return [{
        "id": r.id,
        "user_id": r.user_id,
        "type": r.type,
        "category": r.category,
        "amount": r.amount,
        "note": r.note,
        "date": r.date
    } for r in results]

def fetch_summary(month=None):
    user_id = g.user["id"]
    
    # Base filters
    income_query = db.session.query(db.func.sum(Transaction.amount)).filter_by(user_id=user_id, type='income')
    expense_query = db.session.query(db.func.sum(Transaction.amount)).filter_by(user_id=user_id, type='expense')
    cat_query = db.session.query(Transaction.category, db.func.sum(Transaction.amount).label('total')).filter_by(user_id=user_id, type='expense')

    if month:
        income_query = income_query.filter(Transaction.date.like(f"{month}%"))
        expense_query = expense_query.filter(Transaction.date.like(f"{month}%"))
        cat_query = cat_query.filter(Transaction.date.like(f"{month}%"))

    income = income_query.scalar() or 0
    expense = expense_query.scalar() or 0
    
    cat_rows = cat_query.group_by(Transaction.category).order_by(db.desc('total')).all()
    
    # Monthly trend (last 6 months) - SQLAlchemy version
    # Note: strftime is SQLite specific, for Postgres we'll need to adapt or use cross-compatible logic
    # For now, let's try to stick to something that works on both if possible, or check engine type
    engine_name = db.engine.name
    
    if engine_name == 'sqlite':
        trend_query = db.session.query(
            db.func.strftime('%Y-%m', Transaction.date).label('month'),
            db.func.sum(db.case((Transaction.type == 'income', Transaction.amount), else_=0)).label('income'),
            db.func.sum(db.case((Transaction.type == 'expense', Transaction.amount), else_=0)).label('expense')
        ).filter_by(user_id=user_id)
        
        trend = trend_query.group_by(
            db.func.strftime('%Y-%m', Transaction.date)
        ).order_by(db.desc('month')).limit(6).all()
    else:
        trend_query = db.session.query(
            db.func.to_char(db.func.to_date(Transaction.date, 'YYYY-MM-DD'), 'YYYY-MM').label('month'),
            db.func.sum(db.case((Transaction.type == 'income', Transaction.amount), else_=0)).label('income'),
            db.func.sum(db.case((Transaction.type == 'expense', Transaction.amount), else_=0)).label('expense')
        ).filter_by(user_id=user_id)

        trend = trend_query.group_by(
            db.func.to_char(db.func.to_date(Transaction.date, 'YYYY-MM-DD'), 'YYYY-MM')
        ).order_by(db.desc('month')).limit(6).all()

    return {
        "income": float(income),
        "expense": float(expense),
        "balance": float(income - expense),
        "categories": [{"category": r.category, "total": float(r.total)} for r in cat_rows],
        "trend": [{"month": r.month, "income": float(r.income), "expense": float(r.expense)} for r in reversed(trend)],
    }

def insert_transaction(tx_type, category, amount, note, date):
    user_id = g.user["id"]
    new_tx = Transaction(
        user_id=user_id,
        type=tx_type,
        category=category,
        amount=amount,
        note=note,
        date=date
    )
    db.session.add(new_tx)
    db.session.commit()

def delete_transaction(tx_id):
    user_id = g.user["id"]
    tx = Transaction.query.filter_by(id=tx_id, user_id=user_id).first()
    if tx:
        db.session.delete(tx)
        db.session.commit()

def fetch_available_months():
    user_id = g.user["id"]
    engine_name = db.engine.name
    if engine_name == 'sqlite':
        rows = db.session.query(db.func.strftime('%Y-%m', Transaction.date).label('m'))\
            .filter_by(user_id=user_id).distinct().order_by(db.desc('m')).all()
    else:
        rows = db.session.query(db.func.to_char(db.func.to_date(Transaction.date, 'YYYY-MM-DD'), 'YYYY-MM').label('m'))\
            .filter_by(user_id=user_id).distinct().order_by(db.desc('m')).all()
    return [r.m for r in rows]

def set_limit(category, limit_amount):
    user_id = g.user["id"]
    limit_obj = Limit.query.filter_by(user_id=user_id, category=category).first()
    if limit_obj:
        limit_obj.monthly_limit = limit_amount
    else:
        limit_obj = Limit(user_id=user_id, category=category, monthly_limit=limit_amount)
        db.session.add(limit_obj)
    db.session.commit()

def fetch_limits():
    user_id = g.user["id"]
    rows = Limit.query.filter_by(user_id=user_id).all()
    return {r.category: r.monthly_limit for r in rows}

def check_category_limit_exceeded(category, month=None):
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    user_id = g.user["id"]
    limit_obj = Limit.query.filter_by(user_id=user_id, category=category).first()
    
    if not limit_obj:
        return None
    
    limit = limit_obj.monthly_limit
    
    spent = db.session.query(db.func.sum(Transaction.amount))\
        .filter_by(user_id=user_id, category=category, type='expense')\
        .filter(Transaction.date.like(f"{month}%")).scalar() or 0
    
    if spent > limit:
        return {"category": category, "limit": limit, "spent": float(spent), "exceeded_by": float(spent - limit)}
    
    return None

def store_ai_memory(key, content):
    user_id = g.user["id"]
    memory = AIMemory.query.filter_by(user_id=user_id, key=key, content=content).first()
    if not memory:
        memory = AIMemory(user_id=user_id, key=key, content=content)
        db.session.add(memory)
        db.session.commit()

def fetch_ai_memory(key=None):
    user_id = g.user["id"]
    if key:
        rows = AIMemory.query.filter_by(user_id=user_id, key=key).all()
        return [r.content for r in rows]
    
    rows = AIMemory.query.filter_by(user_id=user_id).all()
    result = {}
    for r in rows:
        if r.key not in result:
            result[r.key] = []
        result[r.key].append(r.content)
    return result

def get_detailed_analytics(month=None):
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    user_id = g.user["id"]
    summary = fetch_summary(month)
    
    # Daily breakdown
    daily_rows = db.session.query(
        Transaction.date,
        db.func.sum(db.case((Transaction.type == 'income', Transaction.amount), else_=0)).label('income'),
        db.func.sum(db.case((Transaction.type == 'expense', Transaction.amount), else_=0)).label('expense')
    ).filter_by(user_id=user_id).filter(Transaction.date.like(f"{month}%"))\
    .group_by(Transaction.date).order_by(Transaction.date).all()
    
    daily_breakdown = [{"date": r.date, "income": float(r.income), "expense": float(r.expense)} for r in daily_rows]
    
    engine_name = db.engine.name
    if engine_name == 'sqlite':
        weekly_rows = db.session.query(
            db.func.strftime('%W', Transaction.date).label('week'),
            db.func.sum(db.case((Transaction.type == 'income', Transaction.amount), else_=0)).label('income'),
            db.func.sum(db.case((Transaction.type == 'expense', Transaction.amount), else_=0)).label('expense')
        ).filter_by(user_id=user_id).filter(Transaction.date.like(f"{month}%"))\
        .group_by(db.func.strftime('%W', Transaction.date)).order_by('week').all()
    else:
        weekly_rows = db.session.query(
            db.func.to_char(db.func.to_date(Transaction.date, 'YYYY-MM-DD'), 'WW').label('week'),
            db.func.sum(db.case((Transaction.type == 'income', Transaction.amount), else_=0)).label('income'),
            db.func.sum(db.case((Transaction.type == 'expense', Transaction.amount), else_=0)).label('expense')
        ).filter_by(user_id=user_id).filter(Transaction.date.like(f"{month}%"))\
        .group_by(db.func.to_char(db.func.to_date(Transaction.date, 'YYYY-MM-DD'), 'WW')).order_by('week').all()
        
    weekly_breakdown = [{"week": r.week, "income": float(r.income), "expense": float(r.expense)} for r in weekly_rows]
    
    # Limit status
    limits = fetch_limits()
    limit_status = []
    
    for category, limit in limits.items():
        spent = db.session.query(db.func.sum(Transaction.amount))\
            .filter_by(user_id=user_id, category=category, type='expense')\
            .filter(Transaction.date.like(f"{month}%")).scalar() or 0
        
        status = "normal"
        if spent > limit:
            status = "exceeded"
        elif spent > limit * 0.9:
            status = "critical"
        elif spent > limit * 0.7:
            status = "warning"
        
        limit_status.append({
            "category": category,
            "limit": float(limit),
            "spent": float(spent),
            "remaining": float(max(0, limit - spent)),
            "percentage": float((spent / limit * 100) if limit > 0 else 0),
            "status": status
        })
    
    limit_status.sort(key=lambda x: x["spent"], reverse=True)
    
    days_elapsed = len(daily_breakdown)
    daily_avg_expense = summary["expense"] / days_elapsed if days_elapsed > 0 else 0
    
    # Simplified projection
    total_days = 30 # Default
    try:
        y, m = map(int, month.split('-'))
        import calendar
        _, total_days = calendar.monthrange(y, m)
    except:
        pass
        
    projected_expense = daily_avg_expense * total_days
    
    return {
        "summary": summary,
        "daily_breakdown": daily_breakdown,
        "weekly_breakdown": weekly_breakdown,
        "limit_status": limit_status,
        "spending_velocity": {
            "daily_average": float(daily_avg_expense),
            "days_elapsed": days_elapsed,
            "total_days_in_month": total_days,
            "projected_expense": float(projected_expense),
            "on_track": projected_expense <= summary["income"] if summary["income"] > 0 else True
        }
    }

def get_expense_warnings():
    month = datetime.now().strftime("%Y-%m")
    user_id = g.user["id"]
    
    warnings = []
    limits = fetch_limits()
    summary = fetch_summary(month)
    
    for category, limit in limits.items():
        spent = db.session.query(db.func.sum(Transaction.amount))\
            .filter_by(user_id=user_id, category=category, type='expense')\
            .filter(Transaction.date.like(f"{month}%")).scalar() or 0
        
        if spent > limit:
            warnings.append({
                "type": "exceeded",
                "category": category,
                "limit": limit,
                "spent": float(spent),
                "exceeded_by": float(spent - limit),
                "message": f"⚠️ CRITICAL: {category} limit exceeded! Spent ₹{spent:.2f} of ₹{limit:.2f} limit (₹{spent-limit:.2f} over)"
            })
        elif spent > limit * 0.9:
            warnings.append({
                "type": "critical",
                "category": category,
                "limit": limit,
                "spent": float(spent),
                "remaining": float(limit - spent),
                "message": f"🔴 CRITICAL: {category} at 90%+! Spent ₹{spent:.2f} of ₹{limit:.2f} (₹{limit-spent:.2f} remaining)"
            })
        elif spent > limit * 0.75:
            warnings.append({
                "type": "warning",
                "category": category,
                "limit": limit,
                "spent": float(spent),
                "remaining": float(limit - spent),
                "message": f"🟡 WARNING: {category} at 75%! Spent ₹{spent:.2f} of ₹{limit:.2f} (₹{limit-spent:.2f} remaining)"
            })
    
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
