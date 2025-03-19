from app.models.user import User
from app.models.curriculum import Subject, Topic, Subtopic
from app.models.task import Task, TaskType, TaskTypePreference, TaskSubtopic

def create_tables():
    """
    Create all database tables based on the defined models.
    This is used for database initialization.
    """
    from app import db
    db.create_all()
    return True
