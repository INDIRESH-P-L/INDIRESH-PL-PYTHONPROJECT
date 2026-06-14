import functools
import re
import secrets
import requests
from datetime import datetime, timedelta
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from .extensions import db
from .models import User
from app import limiter

auth = Blueprint("auth", __name__, url_prefix="/auth")

def _regenerate_session():
    """Regenerate session to prevent session fixation attacks."""
    old_data = dict(session)
    session.clear()
    session.modified = True
    for key, value in old_data.items():
        if key != "user_id":  # Don't copy old user_id
            session[key] = value

def validate_password_strength(password):
    """Validate password meets security requirements."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return "Password must contain an uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must contain a lowercase letter."
    if not re.search(r"\d", password):
        return "Password must contain a number."
    return None

@auth.route("/google/login")
def google_login():
    client_id = current_app.config['GOOGLE_CLIENT_ID']
    redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI', url_for('auth.google_callback', _external=True))
    scope = 'openid email profile'
    response_type = 'code'
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type={response_type}&scope={scope}"
    return redirect(google_auth_url)

@auth.route("/google/callback")
def google_callback():
    code = request.args.get('code')
    if not code:
        flash("Google login failed")
        return redirect(url_for('auth.login'))
        
    client_id = current_app.config['GOOGLE_CLIENT_ID']
    client_secret = current_app.config['GOOGLE_CLIENT_SECRET']
    redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI', url_for('auth.google_callback', _external=True))
    
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    
    token_response = requests.post(token_url, data=token_data).json()
    if 'access_token' not in token_response:
        flash("Failed to retrieve access token from Google.")
        return redirect(url_for('auth.login'))
        
    access_token = token_response['access_token']
    user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    user_info = requests.get(user_info_url, headers={'Authorization': f'Bearer {access_token}'}).json()
    
    if not user_info or 'sub' not in user_info:
        flash("Failed to retrieve user information from Google.")
        return redirect(url_for('auth.login'))

    google_id = user_info['sub']
    email = user_info.get('email', '')
    username = user_info.get('name', email.split('@')[0] if email else 'Google User')

    user = User.query.filter_by(google_id=google_id).first()

    if user is None:
        # Check if user with same email exists
        user = User.query.filter_by(email=email).first()

        if user:
            # Link accounts
            user.google_id = google_id
            db.session.commit()
        else:
            # Create new user
            user = User(username=username, google_id=google_id, email=email, password='')
            db.session.add(user)
            db.session.commit()

    # Security: Regenerate session after login
    _regenerate_session()
    session["user_id"] = user.id
    session.permanent = True  # Use PERMANENT_SESSION_LIFETIME
    return redirect(url_for("index"))

@auth.route("/register", methods=("GET", "POST"))
@limiter.limit("5 per minute")
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        error = None

        if not username:
            error = "Username is required."
        elif len(username) < 3:
            error = "Username must be at least 3 characters."
        elif not password:
            error = "Password is required."
        else:
            # Validate password strength
            password_error = validate_password_strength(password)
            if password_error:
                error = password_error

        if error is None:
            try:
                new_user = User(username=username, password=generate_password_hash(password))
                db.session.add(new_user)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"REGISTER ERROR: {e}")
                error = f"Database Error: {e}"
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template("register.html")

@auth.route("/login", methods=("GET", "POST"))
@limiter.limit("10 per minute")
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        error = None
        user = User.query.filter_by(username=username).first()

        # Security: Use generic error message to prevent user enumeration
        if user is None or not user.password or not check_password_hash(user.password, password):
            error = "Invalid username or password."

        if error is None:
            # Security: Regenerate session after login
            _regenerate_session()
            session["user_id"] = user.id
            session.permanent = True  # Use PERMANENT_SESSION_LIFETIME
            return redirect(url_for("index"))

        flash(error)

    return render_template("login.html")

@auth.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        user = User.query.get(user_id)
        if user:
            g.user = {"id": user.id, "username": user.username, "email": user.email}
        else:
            g.user = None

@auth.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            if request.path.startswith("/api"):
                return jsonify(error="Unauthorized"), 401
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view
