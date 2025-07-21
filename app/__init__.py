from flask import Flask
from config import Config
from jinja2 import StrictUndefined
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.jinja_env.undefined = StrictUndefined
app.config.from_object(Config)
db = SQLAlchemy(app)


from app import views, models

@app.shell_context_processor
def make_shell_context():
    from app.location_utils import reset_db
    return {'db': db, 'Location': models.Location, 'reset_db': reset_db}
