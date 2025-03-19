from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from config.config import configure_app

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
cache = Cache()

def create_app(config_name='default'):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure the app
    configure_app(app, config_name)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    
    # Configure caching
    cache_config = {
        'CACHE_TYPE': app.config.get('CACHE_TYPE', 'SimpleCache'),
        'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_TIMEOUT', 300)
    }
    cache.init_app(app, config=cache_config)
    
    # Enable static file caching
    from app.utils.cache_utils import cache_static_files
    cache_static_files(app, max_age=app.config.get('STATIC_CACHE_TIMEOUT', 86400))
    
    # Register CLI commands
    from app.cli import register_commands
    register_commands(app)
    
    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    from app.routes.curriculum import curriculum
    from app.routes.api.curriculum import curriculum_bp
    from app.routes.db_manage import db_manage_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(curriculum, url_prefix='/curriculum')
    app.register_blueprint(curriculum_bp, url_prefix='/api/curriculum')
    app.register_blueprint(db_manage_bp)
    
    return app
