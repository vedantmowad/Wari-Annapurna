from flask import Flask
from app.config import Config
from app.models.db import mysql

from app.routes.auth_routes import auth_bp
from app.routes.donor_routes import donor_bp
from app.routes.warkari_routes import warkari_bp
from app.routes.admin_routes import admin_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    mysql.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(donor_bp)
    app.register_blueprint(warkari_bp)
    app.register_blueprint(admin_bp)
    return app