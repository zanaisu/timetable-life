"""
Task generator module for creating studying tasks.
Handles task creation, topic selection, and subtopic assignment.
"""

# Import from modular files for better organization
from app.utils.task_subject_utils import get_subject_distribution_for_week
from app.utils.task_topic_utils import select_weighted_topic
from app.utils.task_subtopic_utils import add_subtopics_to_task
from app.utils.task_generator_main import generate_task_for_subject, generate_replacement_task

# Re-export all functions to maintain backward compatibility
__all__ = [
    'get_subject_distribution_for_week',
    'select_weighted_topic',
    'add_subtopics_to_task',
    'generate_task_for_subject',
    'generate_replacement_task'
]
