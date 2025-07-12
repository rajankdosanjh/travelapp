from flask import Flask
from config import Config
from jinja2 import StrictUndefined



app = Flask(__name__)
app.jinja_env.undefined = StrictUndefined
app.config.from_object(Config)
