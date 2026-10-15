import hmac
import os

from flask import Flask, Response, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from . import db
from .config import Config


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Make sure the folder for the database file exists.
    os.makedirs(os.path.dirname(app.config["DATABASE"]) or ".", exist_ok=True)

    if app.config["BEHIND_PROXY"]:
        # Trust one proxy (the Cloudflare Tunnel) for the real scheme and client IP.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    @app.before_request
    def require_password():
        password = app.config["APP_PASSWORD"]
        if not password:
            return None
        auth = request.authorization
        supplied = (auth.password or "") if auth else ""
        if auth and hmac.compare_digest(supplied.encode(), password.encode()):
            return None
        return Response(
            "Password required.",
            401,
            {"WWW-Authenticate": 'Basic realm="Meal Planner"'},
        )

    app.teardown_appcontext(db.close_db)
    with app.app_context():
        db.init_db()

    from .routes import bp

    app.register_blueprint(bp)

    @app.errorhandler(404)
    def not_found(error):
        return render_template(
            "error.html",
            title="Page not found",
            message="That page doesn't exist, or it has been removed.",
        ), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template(
            "error.html",
            title="Something went wrong",
            message="The app hit an unexpected problem. Try again in a moment.",
        ), 500

    return app