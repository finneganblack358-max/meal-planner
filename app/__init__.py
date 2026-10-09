from flask import Flask

from . import db
from .config import Config


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    app.teardown_appcontext(db.close_db)
    with app.app_context():
        db.init_db()

    from .routes import bp

    app.register_blueprint(bp)
    return app