"""
Subtopic utilities for task generation.
Handles subtopic selection and task subtopic management.
"""

from app import db
from app.models.task import TaskSubtopic

def add_subtopics_to_task(task, parent_topic, user, max_duration=None):
    """
    Add subtopics to a task based on estimated duration and confidence levels.
    Prioritizes subtopics with lower confidence levels using the (7 - confidence_level)² formula.
    Respects user's study_hours_per_day and weekend_study_hours preferences.
    
    Args:
        task: Task object to add subtopics to
        parent_topic: Topic object containing subtopics
        user: User object
        max_duration: Maximum duration (in minutes) for the combined subtopics.
                     If None, uses the user's study hours preference.
        
    Returns:
        The updated task object with subtopics added.
    """
    # Determine appropriate max duration based on user preferences
    if max_duration is None:
        from datetime import datetime, timedelta
        
        # Check if today is a weekend (5=Saturday, 6=Sunday)
        today = datetime.utcnow().date()
        is_weekend = today.weekday() >= 5
        
        # Get study hours based on day of week
        if is_weekend and hasattr(user, 'weekend_study_hours'):
            # Use weekend study hours if it's a weekend
            hours = user.weekend_study_hours
        elif hasattr(user, 'study_hours_per_day'):
            # Use weekday study hours
            hours = user.study_hours_per_day
        else:
            # Default if user preferences aren't set
            hours = 2.0 if not is_weekend else 3.0
        
        # Calculate one-third of the total study time (for 3 subjects)
        # This ensures the 3 tasks will fit within the user's preferred study hours
        subject_hours = hours / 3.0
        
        # Convert hours to minutes without an upper limit
        # Just ensure it's at least 15 minutes to accommodate a single subtopic
        max_duration = max(int(subject_hours * 60), 15)

        # Set the task's total_duration to match the target duration
        # This ensures that even if we don't add enough subtopics, the displayed duration is correct
        task.total_duration = max_duration
        
        # If we're generating 3 tasks and each has exactly this duration,
        # the total will match the user's study hour preference
    from app.models.curriculum import Subtopic
    from app.models.confidence import SubtopicConfidence
    import random
    
    # Get all subtopics for this topic
    subtopics = Subtopic.query.filter_by(topic_id=parent_topic.id).all()
    
    if not subtopics:
        return task
    
    try:
        # Get subtopic IDs for confidence query
        subtopic_ids = [s.id for s in subtopics]
        
        # Query confidence data for all subtopics at once
        confidence_data = SubtopicConfidence.query.filter(
            SubtopicConfidence.user_id == user.id,
            SubtopicConfidence.subtopic_id.in_(subtopic_ids)
        ).all()
        
        # Create dictionary for quick lookup
        confidence_dict = {conf.subtopic_id: conf.confidence_level for conf in confidence_data}
        
        # Apply weighting formula (7 - confidence_level)²
        # Higher weight = higher priority for selection
        weighted_subtopics = []
        
        for subtopic in subtopics:
            # Get confidence level (default to 3 if not found - 50% confidence)
            confidence_level = confidence_dict.get(subtopic.id, 3)
            
            # Apply formula: (7 - confidence_level)²
            # This gives higher weights to subtopics with lower confidence
            weight = (7 - confidence_level) ** 2
            
            weighted_subtopics.append((subtopic, weight))
        
        # Sort by weight (descending) to prioritize low-confidence subtopics
        weighted_subtopics.sort(key=lambda x: x[1], reverse=True)
        
        # Extract just the subtopics in their weighted order
        subtopics = [s for s, _ in weighted_subtopics]
        
    except Exception as e:
        # Log the error but don't crash - fall back to random selection
        from flask import current_app
        current_app.logger.error(f"Error in subtopic selection: {str(e)}")
        random.shuffle(subtopics)
    
    # Add subtopics until we reach the max duration
    remaining_duration = max_duration
    added_subtopics = []
    
    for subtopic in subtopics:
        if remaining_duration >= subtopic.estimated_duration and subtopic.title not in added_subtopics:
            task_subtopic = TaskSubtopic(
                task_id=task.id,
                subtopic_id=subtopic.id,
                duration=subtopic.estimated_duration
            )
            db.session.add(task_subtopic)
            
            remaining_duration -= subtopic.estimated_duration
            added_subtopics.append(subtopic.title)
            
            # Stop if we've reached the target duration
            if remaining_duration < 15:  # Minimum subtopic duration
                break
    
    # Commit changes
    db.session.commit()
    
    # Update task description with subtopics
    update_task_description_with_subtopics(task, added_subtopics)
    
    # Force the total duration to match the target duration, even if subtopics don't add up exactly
    task.total_duration = max_duration
    db.session.commit()
    
    return task

def update_task_description_with_subtopics(task, added_subtopics):
    """
    Previously used to update task description with subtopics.
    Now a no-op since subtopics are displayed in their own containers.
    
    Args:
        task: Task object to update
        added_subtopics: List of subtopic titles that were added to the task
        
    Returns:
        None
    """
    # No longer adding subtopics to description since they're displayed separately
    return

def get_subtopics_by_topic(user, topic_id=None):
    """
    Get subtopics for a specific topic or all subtopics.
    
    Args:
        user: User object to get subtopics for
        topic_id: Optional topic ID to filter subtopics by
        
    Returns:
        List of subtopics matching the criteria
    """
    from app.models.curriculum import Subtopic
    
    # Start with a basic query
    query = Subtopic.query
    
    # Filter by topic if specified
    if topic_id is not None:
        query = query.filter_by(topic_id=topic_id)
    
    # Get all subtopics that match the base criteria
    subtopics = query.all()
    
    return subtopics
