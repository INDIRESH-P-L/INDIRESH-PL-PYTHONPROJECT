import sys
import importlib
import logging
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .database import close_db, init_db

# Initialize extensions
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["10000 per day", "1000 per hour"]
)

# Force reimport of models to avoid caching issues
if 'app.models' in sys.modules:
    del sys.modules['app.models']
if 'app.routes' in sys.modules:
    del sys.modules['app.routes']

from .routes   import api


def create_app(config_name="default"):
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Config ────────────────────────────────────────────────────────────────
    from config import config
    app.config.from_object(config[config_name])

    # ── Logging ───────────────────────────────────────────────────────────────
    if config_name == "production":
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)

    # ── Security Extensions ──────────────────────────────────────────────────
    csrf.init_app(app)
    limiter.init_app(app)

    # Exempt API blueprint from CSRF — frontend sends JSON without tokens
    csrf.exempt(api)

    # ── Security Headers ──────────────────────────────────────────────────────
    if config_name == "production":
        try:
            from flask_talisman import Talisman
            # Reasonable CSP for a Flask app with some inline scripts (landing page might have them)
            # Adjust 'unsafe-inline' if you move all JS to files
            csp = {
                'default-src': "'self'",
                'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://accounts.google.com"],
                'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net"],
                'font-src': ["'self'", "https://fonts.gstatic.com"],
                'img-src': ["'self'", "data:", "https://*.googleauth.com"],
                'frame-src': ["https://accounts.google.com"]
            }
            Talisman(app, content_security_policy=csp)
        except ImportError:
            print("Warning: flask-talisman not found, security headers disabled.")

    # ── Database ──────────────────────────────────────────────────────────────
    from .extensions import db
    db.init_app(app)
    
    if config_name != "production":
        from .database import init_db
        init_db(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from .auth import auth
    app.register_blueprint(auth)
    app.register_blueprint(api)

    # ── Page Routes ───────────────────────────────────────────────────────────
    from .auth import login_required

    @app.route("/health")
    def health():
        import os
        return f"Status: Online | DB_URL_SET: {bool(os.environ.get('DATABASE_URL'))}"

    @app.errorhandler(Exception)
    def handle_exception(e):
        import os
        if os.environ.get("FLASK_ENV") == "development" or app.debug:
            import traceback
            return f"<h3>TrackEx Error Debugger</h3><pre>{traceback.format_exc()}</pre>", 500
        else:
            # Production: No tracebacks, just a generic error message
            return render_template("500.html"), 500

    @app.route("/")
    def landing():
        return render_template("landing.html")

    @app.route("/dashboard")
    @login_required
    def index():
        from flask import g
        return render_template("index.html", user=g.user)

    @app.route("/profile")
    @login_required
    def profile():
        from flask import g
        return render_template("profile.html", user=g.user)

    return app
