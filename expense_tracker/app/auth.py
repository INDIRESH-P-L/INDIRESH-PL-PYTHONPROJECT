import functools
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from authlib.integrations.flask_client import OAuth
from .database import get_db

auth = Blueprint("auth", __name__, url_prefix="/auth")

oauth = OAuth()

@auth.record_once
def on_load(state):
    oauth.init_app(state.app)
    oauth.register(
        name='google',
        client_id=state.app.config['GOOGLE_CLIENT_ID'],
        client_secret=state.app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url=state.app.config['GOOGLE_DISCOVERY_URL'],
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

@auth.route("/google/login")
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth.route("/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    if not user_info:
        flash("Failed to retrieve user information from Google.")
        return redirect(url_for('auth.login'))

    google_id = user_info['sub']
    email = user_info['email']
    username = user_info.get('name', email.split('@')[0])

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE google_id = ?", (google_id,)
    ).fetchone()

    if user is None:
        # Check if user with same email exists
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

        if user:
            # Link accounts
            db.execute(
                "UPDATE users SET google_id = ? WHERE id = ?",
                (google_id, user['id'])
            )
            db.commit()
        else:
            # Create new user
            db.execute(
                "INSERT INTO users (username, google_id, email) VALUES (?, ?, ?)",
                (username, google_id, email)
            )
            db.commit()
            user = db.execute(
                "SELECT * FROM users WHERE google_id = ?", (google_id,)
            ).fetchone()

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("index"))

@auth.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        db = get_db()
        error = None

        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."

        if error is None:
            try:
                db.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
            except db.IntegrityError:
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
        db = get_db()
        error = None
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user["password"], password):
            error = "Incorrect password."

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))

        flash(error)

    return render_template("login.html")

@auth.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()

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
