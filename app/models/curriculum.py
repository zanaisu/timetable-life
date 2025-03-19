from app import db
from datetime import datetime
# Note: To avoid circular imports, we won't import the confidence models here

class Subject(db.Model):
    """Model representing a subject in the curriculum."""
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    value = db.Column(db.Integer, default=1)  # Used in the curriculum hierarchy
    is_user_created = db.Column(db.Boolean, default=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Use back_populates instead of backref per SQLAlchemy best practices
    topics = db.relationship('Topic', back_populates='subject', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('Task', back_populates='subject', lazy=True)
    
    def __repr__(self):
        return f"<Subject {self.title}>"

class Topic(db.Model):
    """Model representing a topic within a subject."""
    __tablename__ = 'topics'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    parent_topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    value = db.Column(db.Integer, default=3)  # Used in the curriculum hierarchy
    is_user_created = db.Column(db.Boolean, default=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships - using back_populates for clarity
    subject = db.relationship('Subject', back_populates='topics', lazy=True)
    subtopics = db.relationship('Subtopic', back_populates='topic', lazy=True, cascade='all, delete-orphan')
    child_topics = db.relationship('Topic', backref=db.backref('parent_topic', remote_side=[id]), lazy=True)
    # Confidence relationship
    topic_confidences = db.relationship('TopicConfidence', back_populates='topic', lazy=True, cascade='all, delete-orphan')
    
    def generate_topic_key(self):
        """Generate a unique key for this topic."""
        return f"{self.subject.title}:{self.title}"
    
    def __repr__(self):
        return f"<Topic {self.title}>"

class Subtopic(db.Model):
    """Model representing a subtopic within a topic."""
    __tablename__ = 'subtopics'
    
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    value = db.Column(db.Integer, default=4)  # Used in the curriculum hierarchy
    estimated_duration = db.Column(db.Integer, default=15)  # Duration in minutes
    is_user_created = db.Column(db.Boolean, default=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    topic = db.relationship('Topic', back_populates='subtopics', lazy=True)
    task_subtopics = db.relationship('TaskSubtopic', back_populates='subtopic', lazy=True, cascade='all, delete-orphan')
    # Confidence relationship
    subtopic_confidences = db.relationship('SubtopicConfidence', back_populates='subtopic', lazy=True, cascade='all, delete-orphan')
    
    def generate_subtopic_key(self):
        """Generate a unique key for this subtopic."""
        return f"{self.topic.generate_topic_key()}:{self.title}"
    
    def __repr__(self):
        return f"<Subtopic {self.title}>"

class Exam(db.Model):
    """Model representing exam dates for subjects."""
    __tablename__ = 'exams'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    exam_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to subject
    subject = db.relationship('Subject', backref=db.backref('exams', lazy=True))
    
    def __init__(self, subject_id, title, exam_date):
        self.subject_id = subject_id
        self.title = title
        self.exam_date = exam_date
    
    def __repr__(self):
        return f"<Exam {self.title} for subject_id={self.subject_id} on {self.exam_date}>"
