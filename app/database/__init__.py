from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
import pymysql
pymysql.install_as_MySQLdb()

def init_app(app):
    db.init_app(app)
    with app.app_context():
        # Import models to ensure they are registered with SQLAlchemy
        from . import models