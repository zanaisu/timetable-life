import os
import shutil
import time
import json
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from app import db

# Create blueprint
db_manage_bp = Blueprint('db_manage', __name__, url_prefix='/db')

# Password for authentication
DB_PASSWORD = "693221"

# Cache directory for database files
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'instance', 'db_cache')

# Ensure cache directory exists
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def password_required(f):
    """Decorator to require password authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip password check if env var is set (for CLI mode)
        if os.environ.get('DB_MANAGE_MODE') == 'true':
            return f(*args, **kwargs)
            
        password = request.cookies.get('db_manage_auth')
        # Check if password is in session or in request
        if not password and request.method == 'POST':
            password = request.form.get('password')
        
        if password != DB_PASSWORD:
            return render_template('db_manage/login.html')
        
        return f(*args, **kwargs)
    
    return decorated_function

# Get current database path
def get_db_path():
    db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
    if db_uri.startswith('sqlite:///'):
        # For relative paths (sqlite:///app.db)
        db_file = db_uri.replace('sqlite:///', '')
        if not os.path.isabs(db_file):
            db_file = os.path.join(current_app.instance_path, db_file)
        return db_file
    elif db_uri.startswith('sqlite:////'):
        # For absolute paths (sqlite:////path/to/app.db)
        return db_uri.replace('sqlite:////', '')
    else:
        # For non-SQLite databases, return None
        return None

# Login route
@db_manage_bp.route('/login', methods=['POST'])
def login():
    password = request.form.get('password')
    if password == DB_PASSWORD:
        response = redirect(url_for('db_manage.index'))
        response.set_cookie('db_manage_auth', password, max_age=3600)  # 1 hour expiry
        return response
    else:
        flash('Invalid password', 'error')
        return render_template('db_manage/login.html')

# Main db management page
@db_manage_bp.route('/', methods=['GET'])
@password_required
def index():
    # Get database file info
    db_path = get_db_path()
    db_info = {}
    
    if db_path and os.path.exists(db_path):
        db_size = os.path.getsize(db_path)
        db_mod_time = datetime.fromtimestamp(os.path.getmtime(db_path))
        db_info = {
            'path': db_path,
            'size': f"{db_size / 1024:.2f} KB",
            'modified': db_mod_time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    # Get cached database files
    cached_dbs = []
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith('.db'):
            file_path = os.path.join(CACHE_DIR, filename)
            size = os.path.getsize(file_path)
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            cached_dbs.append({
                'name': filename,
                'size': f"{size / 1024:.2f} KB",
                'modified': mod_time.strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return render_template('db_manage/index.html', 
                          db_info=db_info, 
                          cached_dbs=cached_dbs)

# Export current database
@db_manage_bp.route('/export', methods=['GET'])
@password_required
def export_db():
    db_path = get_db_path()
    if not db_path or not os.path.exists(db_path):
        flash('Database file not found', 'error')
        return redirect(url_for('db_manage.index'))
    
    # Create a timestamp for the filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_filename = f"db_backup_{timestamp}.db"
    
    return send_file(db_path, 
                    as_attachment=True,
                    download_name=export_filename)

# Import database file
@db_manage_bp.route('/import', methods=['POST'])
@password_required
def import_db():
    if 'db_file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('db_manage.index'))
        
    db_file = request.files['db_file']
    
    if db_file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('db_manage.index'))
    
    if not db_file.filename.endswith('.db'):
        flash('Only .db files are supported', 'error')
        return redirect(url_for('db_manage.index'))
    
    # Save file to cache first
    filename = secure_filename(db_file.filename)
    cache_path = os.path.join(CACHE_DIR, filename)
    db_file.save(cache_path)
    
    # Option to apply immediately
    apply_immediately = request.form.get('apply_immediately') == 'on'
    
    if apply_immediately:
        return _apply_db(filename)
    
    flash(f'Database file "{filename}" imported to cache', 'success')
    return redirect(url_for('db_manage.index'))

# Cache current database
@db_manage_bp.route('/cache-current', methods=['POST'])
@password_required
def cache_current():
    db_path = get_db_path()
    if not db_path or not os.path.exists(db_path):
        flash('Database file not found', 'error')
        return redirect(url_for('db_manage.index'))
    
    # Create a filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"db_cache_{timestamp}.db"
    cache_path = os.path.join(CACHE_DIR, filename)
    
    # Copy the current database to cache
    shutil.copy2(db_path, cache_path)
    
    flash(f'Current database cached as "{filename}"', 'success')
    return redirect(url_for('db_manage.index'))

# Apply cached database
@db_manage_bp.route('/apply/<filename>', methods=['POST'])
@password_required
def apply_db(filename):
    return _apply_db(filename)

def _apply_db(filename):
    """Helper to apply a cached DB file to the current database"""
    db_path = get_db_path()
    if not db_path:
        flash('Current database configuration not supported', 'error')
        return redirect(url_for('db_manage.index'))
    
    cache_path = os.path.join(CACHE_DIR, secure_filename(filename))
    if not os.path.exists(cache_path):
        flash(f'Cached database file "{filename}" not found', 'error')
        return redirect(url_for('db_manage.index'))
    
    # Backup current database first
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"db_backup_before_apply_{timestamp}.db"
    backup_path = os.path.join(CACHE_DIR, backup_filename)
    
    # Only backup if the current database exists
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
    
    # Close any database connections
    db.session.close()
    db.engine.dispose()
    
    # Apply the cached database
    try:
        shutil.copy2(cache_path, db_path)
        flash(f'Database "{filename}" applied successfully (backup created as "{backup_filename}")', 'success')
        
        # Check if we need to restart the app
        restart = request.form.get('restart_app') == 'on'
        if restart:
            # Redirect to a special endpoint that will restart the application
            return redirect(url_for('db_manage.restart_app'))
        
        return redirect(url_for('db_manage.index'))
    except Exception as e:
        flash(f'Error applying database: {str(e)}', 'error')
        return redirect(url_for('db_manage.index'))

# Delete cached database
@db_manage_bp.route('/delete/<filename>', methods=['POST'])
@password_required
def delete_cached(filename):
    cache_path = os.path.join(CACHE_DIR, secure_filename(filename))
    if not os.path.exists(cache_path):
        flash(f'Cached database file "{filename}" not found', 'error')
        return redirect(url_for('db_manage.index'))
    
    try:
        os.remove(cache_path)
        flash(f'Cached database "{filename}" deleted', 'success')
    except Exception as e:
        flash(f'Error deleting cached database: {str(e)}', 'error')
    
    return redirect(url_for('db_manage.index'))

# Restart the application
@db_manage_bp.route('/restart', methods=['GET'])
@password_required
def restart_app():
    # This is a placeholder view for the restart page
    return render_template('db_manage/restart.html') 