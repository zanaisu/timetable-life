import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Default to SQLite database for development simplicity
    SQLALCHEMY_DATABASE_URI = os.environ.get('LOCAL_DATABASE_URI', 'sqlite:///app.db')
    
    # Caching configuration
    CACHE_TYPE = 'SimpleCache'  # Simple memory cache
    CACHE_DEFAULT_TIMEOUT = 300  # Default timeout in seconds
    STATIC_CACHE_TIMEOUT = 86400  # 1 day cache for static files


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    # Shorter cache timeout for development
    CACHE_DEFAULT_TIMEOUT = 60
    STATIC_CACHE_TIMEOUT = 3600  # 1 hour for development


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # Disable caching for testing
    CACHE_TYPE = 'NullCache'
    STATIC_CACHE_TIMEOUT = 0  # No caching for testing


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    # Use SQLite for production as well (no external database)
    SQLALCHEMY_DATABASE_URI = os.environ.get('LOCAL_DATABASE_URI', 'sqlite:///app.db')
    # Production caching settings
    CACHE_TYPE = 'SimpleCache'  # You can use 'RedisCache' if Redis is available
    CACHE_DEFAULT_TIMEOUT = 600  # 10 minutes
    STATIC_CACHE_TIMEOUT = 604800  # 7 days for production


# Configuration dictionary to easily access different configs
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_database_uri(environment='default'):
    """Helper function to get the correct database URI based on environment."""
    return config[environment].SQLALCHEMY_DATABASE_URI


def configure_app(app, environment='default'):
    """Configure the Flask application with the specified environment."""
    app.config.from_object(config[environment])
    app.config['ENVIRONMENT'] = environment
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass