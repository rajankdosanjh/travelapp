from flask import Flask, request
from config import Config
from jinja2 import StrictUndefined
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import sqlalchemy as sa



app = Flask(__name__)
app.jinja_env.undefined = StrictUndefined
app.config.from_object(Config)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@app.before_request
def handle_api_preflight():
    if request.method == "OPTIONS" and request.path.startswith("/api/"):
        return app.make_response(("", 204))


@app.after_request
def add_api_cors_headers(response):
    if request.path.startswith("/api/"):
        response.headers["Access-Control-Allow-Origin"] = app.config.get("API_CORS_ORIGINS", "*")
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return response

def ensure_location_schema():
    with app.app_context():
        if db.engine.dialect.name != "sqlite":
            return
        columns = db.session.execute(sa.text("PRAGMA table_info(locations)")).fetchall()
        if not columns:
            return
        column_names = {col[1] for col in columns}
        if 'address' not in column_names:
            db.session.execute(sa.text("ALTER TABLE locations ADD COLUMN address VARCHAR(200)"))
            db.session.commit()

def ensure_social_schema():
    with app.app_context():
        db.create_all()

def ensure_public_route_schema():
    with app.app_context():
        if db.engine.dialect.name != "sqlite":
            return
        columns = db.session.execute(sa.text("PRAGMA table_info(saved_routes)")).fetchall()
        if not columns:
            return
        column_names = {col[1] for col in columns}
        if 'is_public' not in column_names:
            db.session.execute(sa.text("ALTER TABLE saved_routes ADD COLUMN is_public BOOLEAN DEFAULT 0"))
            db.session.commit()

def ensure_saved_place_schema():
    with app.app_context():
        if db.engine.dialect.name != "sqlite":
            return
        columns = db.session.execute(sa.text("PRAGMA table_info(saved_places)")).fetchall()
        if not columns:
            return
        column_names = {col[1] for col in columns}
        if 'photo_filename' not in column_names:
            db.session.execute(sa.text("ALTER TABLE saved_places ADD COLUMN photo_filename VARCHAR(200)"))
            db.session.commit()


from app import views, models
from app.api import api_bp
ensure_location_schema()
ensure_social_schema()
ensure_public_route_schema()
ensure_saved_place_schema()
app.register_blueprint(api_bp)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(models.User, int(user_id))

@app.shell_context_processor
def make_shell_context():
    from app.location_utils import reset_db
    return {'db': db, 'Location': models.Location, 'reset_db': reset_db}
