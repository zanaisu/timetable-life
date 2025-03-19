from datetime import datetime
from app import db

class TaskType(db.Model):
    """Model representing different types of tasks (notes, quiz, practice, uplearn)."""
    __tablename__ = 'task_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    
    # Relationships
    preferences = db.relationship('TaskTypePreference', backref='task_type', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='task_type', lazy=True)
    
    def __init__(self, name, description=None):
        self.name = name
        self.description = description
    
    @classmethod
    def get_uplearn_id(cls):
        """Get the ID of the Uplearn task type."""
        uplearn = cls.query.filter_by(name='uplearn').first()
        if uplearn:
            return uplearn.id
        return None
    
    @classmethod
    def create_default_types(cls):
        """Create default task types if they don't exist."""
        default_types = [
            ('notes', 'Taking or reviewing notes on a topic'),
            ('quiz', 'Testing knowledge through questions'),
            ('practice', 'Applying knowledge through practice problems'),
            ('uplearn', 'Completing Uplearn modules')
        ]
        
        for name, description in default_types:
            if not cls.query.filter_by(name=name).first():
                task_type = cls(name=name, description=description)
                db.session.add(task_type)
        
        db.session.commit()
    
    def __repr__(self):
        return f"<TaskType {self.name}>"


class TaskTypePreference(db.Model):
    """Model tracking user preferences for task types by subject."""
    __tablename__ = 'task_type_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_type_id = db.Column(db.Integer, db.ForeignKey('task_types.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)  # Null for global preference
    is_enabled = db.Column(db.Boolean, default=True)
    
    def __init__(self, user_id, task_type_id, subject_id=None, is_enabled=True):
        self.user_id = user_id
        self.task_type_id = task_type_id
        self.subject_id = subject_id
        self.is_enabled = is_enabled
    
    def __repr__(self):
        return f"<TaskTypePreference user={self.user_id} type={self.task_type_id} subject={self.subject_id if self.subject_id else 'global'}>"


class Task(db.Model):
    """Model representing a study task."""
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=True)
    task_type_id = db.Column(db.Integer, db.ForeignKey('task_types.id'), nullable=False)
    
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    total_duration = db.Column(db.Integer, default=30)  # Duration in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    skipped_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    subject = db.relationship('Subject', back_populates='tasks')
    topic = db.relationship('Topic', backref=db.backref('tasks', lazy=True))
    subtopics = db.relationship('TaskSubtopic', backref='task', lazy=True, cascade='all, delete-orphan')
    # Explicitly define the relationship to User
    assigned_user = db.relationship('User', back_populates='tasks')
    
    def __init__(self, user_id, subject_id, task_type_id, title, description=None, topic_id=None, due_date=None, total_duration=30):
        self.user_id = user_id
        self.subject_id = subject_id
        self.task_type_id = task_type_id
        self.title = title
        self.description = description
        self.topic_id = topic_id
        self.due_date = due_date
        self.total_duration = total_duration
    
    def mark_completed(self):
        """Mark the task as completed and load relationships."""
        self.completed_at = datetime.utcnow()
        
        # Ensure subtopics relationship is loaded
        if not hasattr(self, '_subtopics_loaded'):
            _ = self.subtopics  # Access relationship to load it
            self._subtopics_loaded = True
        
        db.session.commit()
    
    def mark_skipped(self):
        """Mark the task as skipped."""
        self.skipped_at = datetime.utcnow()
        db.session.commit()
    
    def add_subtopic(self, subtopic_id, duration=15):
        """Add a subtopic to this task."""
        task_subtopic = TaskSubtopic(
            task_id=self.id,
            subtopic_id=subtopic_id,
            duration=duration
        )
        db.session.add(task_subtopic)
        db.session.commit()
        
        # Update the total task duration
        self.update_total_duration()
    
    def update_total_duration(self):
        """Update the total duration based on subtopic durations."""
        total = sum(ts.duration for ts in self.subtopics)
        self.total_duration = total if total > 0 else 30
        db.session.commit()
    
    def get_subtopics(self):
        """Get all subtopics in this task."""
        result = []
        
        for task_subtopic in self.subtopics:
            from app.models.curriculum import Subtopic
            subtopic = Subtopic.query.get(task_subtopic.subtopic_id)
            if subtopic:
                result.append(subtopic)
        
        return result
    
    def is_active(self):
        """Check if this task is still active (not completed or skipped)."""
        return not self.completed_at and not self.skipped_at
    
    @property
    def is_completed(self):
        """Check if this task is completed."""
        return self.completed_at is not None
    
    def __repr__(self):
        return f"<Task {self.id}: {self.title}>"


class TaskSubtopic(db.Model):
    """Model linking tasks to subtopics with durations."""
    __tablename__ = 'task_subtopics'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    subtopic_id = db.Column(db.Integer, db.ForeignKey('subtopics.id'), nullable=False)
    duration = db.Column(db.Integer, default=15)  # Duration in minutes
    
    # Relationships
    subtopic = db.relationship('Subtopic', back_populates='task_subtopics', lazy=True)
    
    def __init__(self, task_id, subtopic_id, duration=15):
        self.task_id = task_id
        self.subtopic_id = subtopic_id
        self.duration = duration
    
    def __repr__(self):
        return f"<TaskSubtopic task={self.task_id} subtopic={self.subtopic_id}>"
