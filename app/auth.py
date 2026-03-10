import functools
import requests
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from .extensions import db
from .models import User

auth = Blueprint("auth", __name__, url_prefix="/auth")

@auth.route("/google/login")
def google_login():
    client_id = current_app.config['GOOGLE_CLIENT_ID']
    redirect_uri = url_for('auth.google_callback', _external=True)
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
    redirect_uri = url_for('auth.google_callback', _external=True)
    
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

    session.clear()
    session["user_id"] = user.id
    return redirect(url_for("index"))

@auth.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        error = None

        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."

        if error is None:
            try:
                new_user = User(username=username, password=generate_password_hash(password))
                db.session.add(new_user)
                db.session.commit()
            except Exception:
                db.session.rollback()
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template("register.html")

@auth.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        error = None
        user = User.query.filter_by(username=username).first()

        if user is None:
            error = "Incorrect username."
        elif not user.password or not check_password_hash(user.password, password):
            error = "Incorrect password."

        if error is None:
            session.clear()
            session["user_id"] = user.id
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
