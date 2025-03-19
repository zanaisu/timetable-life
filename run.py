import os
import sys
import threading
import webbrowser
import time
import subprocess
from dotenv import load_dotenv
from app import create_app, db
from sqlalchemy import inspect
from app.utils.data_import import seed_default_data, verify_imported_data
from app.utils.curriculum_importer import import_curriculum_data as import_jsonc_curriculum

# Load environment variables
load_dotenv()

# Create app with appropriate config
env = os.environ.get('FLASK_ENV', 'development')

    
print(f"Using environment: {env}")
app = create_app(env)

# Database management functions are now handled by the db-manage interface

@app.cli.command('import-curriculum')
def import_curriculum():
    """Import curriculum data from JSONC file."""
    from flask import current_app
    
    with app.app_context():
        success, message = import_jsonc_curriculum()
        if success:
            current_app.logger.info(message)
        else:
            current_app.logger.error(message)

@app.cli.command('verify-data')
def verify_data():
    """Verify the integrity of imported curriculum data."""
    from flask import current_app
    from app.utils.data_import import verify_imported_data
    
    with app.app_context():
        # Verify data
        verification = verify_imported_data()
        
        if not verification['success']:
            current_app.logger.error(f"Data verification failed: {verification['issues']}")
        elif verification['issues']:
            current_app.logger.warning(f"Verification warnings: {verification['issues']}")
        else:
            current_app.logger.info("Data verification successful")

@app.cli.command('db-manage')
def db_manage():
    """Open the database management interface in a browser."""
    import click
    
    click.echo('Starting database management interface...')
    
    # Set environment variables
    env = os.environ.copy()
    env['DB_MANAGE_MODE'] = 'true'
    env['FLASK_APP'] = 'run.py'
    
    # Define the URL for the database management interface
    db_manage_url = 'http://localhost:5000/db'
    
    # Function to open browser after a delay to ensure server is running
    def open_browser():
        time.sleep(2)  # Wait for server to start
        click.echo(f'Opening database management interface at {db_manage_url}')
        webbrowser.open(db_manage_url)
    
    # Start the browser opener in a separate thread
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Run Flask using subprocess
    click.echo('Starting Flask development server...')
    try:
        # Use Python executable that's running this script
        python_exe = sys.executable
        subprocess.run([python_exe, '-m', 'flask', 'run', '--host=0.0.0.0', '--port=5000'], 
                      env=env, check=True)
    except KeyboardInterrupt:
        click.echo('Server stopped by user.')
    except subprocess.CalledProcessError as e:
        click.echo(f'Error running server: {e}')
    except Exception as e:
        click.echo(f'Unexpected error: {e}')

if __name__ == '__main__':
    app.run(debug=True)
