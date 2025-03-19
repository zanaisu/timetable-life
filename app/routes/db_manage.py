import os
import shutil
import time
import json
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from app import db
from app.utils.curriculum_importer import import_curriculum_data
from app.models.task import TaskType
from app.utils.database_helpers import fill_database

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

# Import curriculum data
@db_manage_bp.route('/import-curriculum', methods=['POST'])
@password_required
def import_curriculum():
    """Import curriculum data into the database."""
    try:
        success, message = import_curriculum_data()
        
        if success:
            flash(f'Curriculum import successful: {message}', 'success')
        else:
            flash(f'Curriculum import failed: {message}', 'error')
    except Exception as e:
        flash(f'Error importing curriculum data: {str(e)}', 'error')
        
    return redirect(url_for('db_manage.index'))

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

# Get database structure
@db_manage_bp.route('/inspect', methods=['GET'])
@password_required
def inspect_db():
    """Get structure of the current database"""
    db_path = get_db_path()
    if not db_path or not os.path.exists(db_path):
        flash('Database file not found', 'error')
        return redirect(url_for('db_manage.index'))
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        structure = {}
        
        # Get columns for each table
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            # Count rows in the table
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            row_count = cursor.fetchone()[0]
            
            structure[table_name] = {
                'columns': [{'name': col[1], 'type': col[2]} for col in columns],
                'row_count': row_count
            }
        
        conn.close()
        return jsonify(structure)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# View table data
@db_manage_bp.route('/table/<table_name>', methods=['GET'])
@password_required
def view_table(table_name):
    """View data in a specific table"""
    db_path = get_db_path()
    if not db_path or not os.path.exists(db_path):
        flash('Database file not found', 'error')
        return redirect(url_for('db_manage.index'))
    
    try:
        # Get page parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        offset = (page - 1) * per_page
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        # Get total row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        total_rows = cursor.fetchone()[0]
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Get data with pagination
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {per_page} OFFSET {offset};")
        rows = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # Calculate pagination info
        total_pages = (total_rows + per_page - 1) // per_page
        
        return jsonify({
            'table_name': table_name,
            'columns': columns,
            'rows': rows,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_rows': total_rows,
                'total_pages': total_pages
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# List all database files in cache with more details
@db_manage_bp.route('/cache-list', methods=['GET'])
@password_required
def list_cached_dbs():
    """Get a detailed list of all cached database files"""
    cached_dbs = []
    
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith('.db'):
            file_path = os.path.join(CACHE_DIR, filename)
            stats = os.stat(file_path)
            size = stats.st_size
            created_time = datetime.fromtimestamp(stats.st_ctime)
            modified_time = datetime.fromtimestamp(stats.st_mtime)
            
            # Try to get table count
            table_count = 0
            try:
                conn = sqlite3.connect(file_path)
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
                table_count = cursor.fetchone()[0]
                conn.close()
            except:
                pass
            
            cached_dbs.append({
                'name': filename,
                'size': size,
                'size_formatted': f"{size / 1024:.2f} KB",
                'created': created_time.isoformat(),
                'created_formatted': created_time.strftime('%Y-%m-%d %H:%M:%S'),
                'modified': modified_time.isoformat(),
                'modified_formatted': modified_time.strftime('%Y-%m-%d %H:%M:%S'),
                'table_count': table_count
            })
    
    # Sort by modified time (newest first)
    cached_dbs.sort(key=lambda x: x['modified'], reverse=True)
    
    return jsonify(cached_dbs)

@db_manage_bp.route('/restart', methods=['GET'])
@password_required
def restart_app():
    # This is a placeholder view for the restart page
    return render_template('db_manage/restart.html')

# Initialize a new empty database
@db_manage_bp.route('/initialize', methods=['POST'])
@password_required
def initialize_db():
    """Initialize a fresh database"""
    db_path = get_db_path()
    if not db_path:
        flash('Current database configuration not supported', 'error')
        return redirect(url_for('db_manage.index'))
    
    # Backup current database first if it exists
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"db_backup_before_initialize_{timestamp}.db"
        backup_path = os.path.join(CACHE_DIR, backup_filename)
        try:
            shutil.copy2(db_path, backup_path)
            flash(f'Backed up existing database as "{backup_filename}"', 'success')
        except Exception as e:
            flash(f'Could not backup existing database: {str(e)}', 'error')
    
    # Close any database connections
    try:
        db.session.close()
        db.engine.dispose()
        
        # Give the system a moment to release file locks (Windows specific)
        import time
        time.sleep(1)
        
        # On Windows, sometimes we need a more aggressive approach
        import gc
        gc.collect()  # Force garbage collection
        
        # Remove existing database if it exists
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except PermissionError:
                # If still can't delete, inform the user
                flash('Unable to delete the existing database file - it may be in use by another process. ' +
                      'Try closing all applications that might be using it and try again.', 'error')
                return redirect(url_for('db_manage.index'))
        
        # Recreate the database and initialize tables
        from app import create_app
        from app.models import create_tables
        
        app = create_app()
        with app.app_context():
            create_tables()
        
        flash('Database initialized successfully with empty tables', 'success')
    except Exception as e:
        flash(f'Error initializing database: {str(e)}', 'error')
    
    return redirect(url_for('db_manage.index'))

# Repair database by ensuring default types exist
@db_manage_bp.route('/repair', methods=['POST'])
@password_required
def repair_database():
    """Repair the database by ensuring all default data exists."""
    try:
        # Ensure the database tables exist
        from app.models import create_tables
        create_tables()
        
        # Create default task types
        TaskType.create_default_types()
        
        flash('Database repaired successfully: tables and default task types created', 'success')
        
        # Perform any other database repairs or migrations here
        
        return redirect(url_for('db_manage.index'))
    except Exception as e:
        flash(f'Error repairing database: {str(e)}', 'error')
        return redirect(url_for('db_manage.index'))

# Combined function to fill database (repair + import curriculum)
@db_manage_bp.route('/fill', methods=['POST'])
@password_required
def fill_db():
    """Fill the database with all required data including curriculum."""
    success, message = fill_database()
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('db_manage.index')) 