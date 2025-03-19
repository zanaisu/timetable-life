from datetime import datetime
from flask_login import UserMixin
from app import db, bcrypt, login_manager
from app.models.task import TaskTypePreference, TaskType
from app.models.confidence import SubtopicConfidence, TopicConfidence

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    """User model for authentication and preferences."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(100), unique=False, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Study preferences
    study_hours_per_day = db.Column(db.Float, default=2.0)
    weekend_study_hours = db.Column(db.Float, default=3.0)
    
    # UI preferences
    dark_mode = db.Column(db.Boolean, default=False)
    
    # Relationships
    task_type_preferences = db.relationship('TaskTypePreference', backref='user', lazy=True, cascade='all, delete-orphan')
    # Using explicit back_populates to avoid backref conflicts
    tasks = db.relationship('Task', back_populates='assigned_user', lazy=True, cascade='all, delete-orphan')
    # Confidence relationships
    subtopic_confidences = db.relationship('SubtopicConfidence', back_populates='user', lazy=True, cascade='all, delete-orphan')
    topic_confidences = db.relationship('TopicConfidence', back_populates='user', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, username, password, email=None):
        self.username = username
        self.set_password(password)
        self.email = email
    
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update the last login time."""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def get_enabled_task_types(self):
        """Get a list of task types enabled for this user."""
        return [pref.task_type for pref in self.task_type_preferences if pref.is_enabled]
    
    def is_uplearn_enabled_for_subject(self, subject_id):
        """Check if Uplearn is enabled for a specific subject."""
        uplearn_pref = TaskTypePreference.query.filter_by(
            user_id=self.id, 
            subject_id=subject_id, 
            task_type_id=TaskType.get_uplearn_id()
        ).first()
        
        return uplearn_pref and uplearn_pref.is_enabled
    
    def __repr__(self):
        return f"<User {self.username}>"
