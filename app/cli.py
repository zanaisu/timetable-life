import click
import os
import threading
import subprocess
import webbrowser
import time
import sys
from flask.cli import with_appcontext
from app.utils.curriculum_importer import import_curriculum_data
from app import db, migrate

def register_commands(app):
    """Register Flask CLI commands."""
    
    # The db-init command has been removed as it's now handled by the db-manage interface
    
    @app.cli.command('import-curriculum')
    @with_appcontext
    def import_curriculum():
        """Import curriculum data from JSONC file."""
        click.echo('Importing curriculum data...')
        success, message = import_curriculum_data()
        
        if success:
            click.echo(click.style(message, fg='green'))
        else:
            click.echo(click.style(f"Error: {message}", fg='red'))
    
    # Database functions are now handled by the db-manage interface
    
    @app.cli.command('db-manage')
    def db_manage():
        """Open the database management interface in a browser."""
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
