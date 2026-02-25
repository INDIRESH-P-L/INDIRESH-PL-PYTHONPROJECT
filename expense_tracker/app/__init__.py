from flask import Flask, render_template
from .database import close_db, init_db
from .routes   import api


def create_app(config_name="default"):
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Config ────────────────────────────────────────────────────────────────
    from config import config
    app.config.from_object(config[config_name])

    # ── Database ──────────────────────────────────────────────────────────────
    app.teardown_appcontext(close_db)
    init_db(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from .auth import auth
    app.register_blueprint(auth)
    app.register_blueprint(api)

    # ── Page Routes ───────────────────────────────────────────────────────────
    from .auth import login_required

    @app.route("/")
    @login_required
    def index():
        from flask import g
        return render_template("index.html", user=g.user)

    return app
