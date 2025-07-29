import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or b'WR#&f&+%78er0we=%799eww+#7^90-;s'

    # Path to the new locations CSV file
    LOCATIONS_CSV_PATH = os.path.join(basedir, 'app', 'data', 'locations.csv')

    # Keep the original instance folder for the database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data.sqlite'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to False for cleaner terminal output
