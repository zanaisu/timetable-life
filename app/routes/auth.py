from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from app import db, bcrypt
from app.models.user import User
from app.models.task import TaskType, TaskTypePreference

# Create blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.update_last_login()
            
            next_page = request.args.get('next')
            
            # Check if first login to redirect to setup
            if not session.get('setup_complete', False) and user.created_at == user.last_login:
                return redirect(url_for('main.first_login_setup'))
            
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout route that logs the user out and redirects to the login page."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """New user registration route."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        email = request.form.get('email')
        
        # Basic validation
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('auth/register.html')
        
        if password != password_confirm:
            flash('Passwords do not match', 'danger')
            return render_template('auth/register.html')
        
        # Check for existing user
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'danger')
            return render_template('auth/register.html')
        
        # Check for empty email and convert to None
        if email is not None and email.strip() == '':
            email = None
        
        if email:
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash('Email already in use', 'danger')
                return render_template('auth/register.html')
        
        # Create new user
        user = User(username=username, password=password, email=email)
        db.session.add(user)
        db.session.commit()
        
        # Initialize task type preferences
        task_types = TaskType.query.all()
        for task_type in task_types:
            # Create global preference for this task type
            preference = TaskTypePreference(
                user_id=user.id,
                task_type_id=task_type.id,
                is_enabled=True
            )
            db.session.add(preference)
        
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')
