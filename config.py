import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or b'WR#&f&+%78er0we=%799eww+#7^90-;s'

    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    # Keep the original instance folder for the database
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///' + os.path.join(basedir, 'app', 'data', 'data.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to False for cleaner terminal output
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'data', 'user_uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    API_TOKEN_MAX_AGE = int(os.environ.get('API_TOKEN_MAX_AGE', 60 * 60 * 24 * 14))
    API_CORS_ORIGINS = os.environ.get('API_CORS_ORIGINS', '*')
    ORS_API_KEY = os.environ.get('ORS_API_KEY')

    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'
    REMEMBER_COOKIE_SECURE = os.environ.get('REMEMBER_COOKIE_SECURE', '0') == '1'
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    PREFERRED_URL_SCHEME = os.environ.get('PREFERRED_URL_SCHEME', 'http')
