from flask import Flask
from config import Config
from jinja2 import StrictUndefined
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager



app = Flask(__name__)
app.jinja_env.undefined = StrictUndefined
app.config.from_object(Config)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


from app import views, models

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(models.User, int(user_id))

@app.shell_context_processor
def make_shell_context():
    from app.location_utils import reset_db
    return {'db': db, 'Location': models.Location, 'reset_db': reset_db}
