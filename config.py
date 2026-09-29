import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key_if_missing')
    from datetime import timedelta
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_REFRESH_EACH_REQUEST = True
    
    # Environment-aware security config
    is_production = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_SECURE = is_production
    REMEMBER_COOKIE_SECURE = is_production
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Construct PostgreSQL URI from environment variables
    # Format: postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DATABASE_NAME
    # Note: Using psycopg2-binary adapter
    db_user = os.environ.get('DATABASE_USER', 'postgres')
    db_password = os.environ.get('DATABASE_PASSWORD', '')
    db_host = os.environ.get('DATABASE_HOST', 'localhost')
    db_port = os.environ.get('DATABASE_PORT', '5432')
    db_name = os.environ.get('DATABASE_NAME', 'medibridge')

    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Google OAuth 2.0 Credentials
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')
