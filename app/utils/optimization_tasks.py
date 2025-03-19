"""
Task optimization utilities for efficient task generation.
Provides functions for generating tasks in batches with proper transaction handling.
"""

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.utils.optimization_queries import get_optimized_subject_distribution
from app.utils.optimization_batch import db_batch_process, db_batch_update
from datetime import datetime, timedelta

def generate_tasks_in_batch(user_id, count=5, max_retries=3):
    """
    Generate multiple tasks at once for a user with transaction safety.
    More efficient than generating tasks one by one.
    
    Args:
        user_id: User ID to generate tasks for
        count: Number of tasks to generate
        max_retries: Maximum number of retry attempts for failed operations
        
    Returns:
        Dict with status and generated tasks
    """
    from app.utils.task_generator import generate_replacement_task
    from app.models.user import User
    
    result = {
        'success': True,
        'tasks': [],
        'error': None
    }
    
    # Get the user object
    user = User.query.get(user_id)
    if not user:
        result['success'] = False
        result['error'] = f"User with ID {user_id} not found"
        return result
    
    # Get subject distribution with caching
    try:
        distribution = get_optimized_subject_distribution(user_id)
    except Exception as e:
        current_app.logger.error(f"Error getting subject distribution: {str(e)}")
        distribution = {}  # Use empty distribution as fallback
    
    # Generate tasks with retry logic
    retry_count = 0
    successful_tasks = 0
    
    while successful_tasks < count and retry_count <= max_retries:
        try:
            # Start a new transaction for each attempt
            db.session.begin_nested()
            
            # Calculate how many more tasks we need
            remaining = count - successful_tasks
            
            # Generate the remaining tasks
            for _ in range(remaining):
                task = generate_replacement_task(user)
                if task:
                    result['tasks'].append(task)
                    successful_tasks += 1
            
            # Commit the transaction if we generated at least one task
            if successful_tasks > 0:
                db.session.commit()
                retry_count = 0  # Reset retry counter after success
            else:
                # No tasks generated, so rollback and try again
                db.session.rollback()
                retry_count += 1
                current_app.logger.warning(f"No tasks generated, retrying (attempt {retry_count}/{max_retries})...")
        
        except Exception as e:
            # Rollback on error
            db.session.rollback()
            current_app.logger.error(f"Error generating tasks: {str(e)}")
            
            # Retry logic
            if retry_count < max_retries:
                retry_count += 1
                current_app.logger.info(f"Retrying task generation (attempt {retry_count}/{max_retries})...")
            else:
                result['success'] = False
                result['error'] = f"Failed to generate all requested tasks after {max_retries} retries"
                break
    
    # If we generated some tasks but not all, consider it a partial success
    if 0 < successful_tasks < count:
        result['success'] = True
        result['error'] = f"Only generated {successful_tasks}/{count} tasks"
    
    return result

def generate_balanced_task_batch(user_id, count=5, max_per_subject=2):
    """
    Generate a balanced batch of tasks across different subjects.
    Ensures no single subject dominates the task list.
    
    Args:
        user_id: User ID to generate tasks for
        count: Total number of tasks to generate
        max_per_subject: Maximum tasks for any single subject
        
    Returns:
        List of generated tasks
    """
    from app.utils.task_generator import generate_task_for_subject
    from app.models.user import User
    from app.models.curriculum import Subject
    
    # Get the user object
    user = User.query.get(user_id)
    if not user:
        return []
    
    # Get distribution to prioritize subjects
    distribution = get_optimized_subject_distribution(user_id)
    
    # Get all subjects and sort by distribution weight
    subjects = Subject.query.all()
    if not subjects:
        return []
    
    weighted_subjects = [(s, distribution.get(s.id, 0)) for s in subjects]
    weighted_subjects.sort(key=lambda x: x[1], reverse=True)
    
    # Generate tasks
    tasks = []
    subject_counts = {}
    
    # First pass - try to generate at least one task per subject
    for subject, _ in weighted_subjects:
        if len(tasks) >= count:
            break
            
        task = generate_task_for_subject(user, subject.id)
        if task:
            tasks.append(task)
            subject_counts[subject.id] = 1
    
    # Second pass - fill remaining slots while respecting max_per_subject
    remaining_slots = count - len(tasks)
    if remaining_slots > 0:
        for subject, weight in weighted_subjects:
            if len(tasks) >= count:
                break
                
            # Skip if we've reached max for this subject
            if subject_counts.get(subject.id, 0) >= max_per_subject:
                continue
                
            task = generate_task_for_subject(user, subject.id)
            if task:
                tasks.append(task)
                subject_counts[subject.id] = subject_counts.get(subject.id, 0) + 1
                
                if len(tasks) >= count:
                    break
    
    return tasks

def regenerate_stale_tasks(user_id, days_threshold=7, limit=10, batch_size=5):
    """
    Find and regenerate tasks that haven't been updated in a while.
    Uses batch processing for better performance and transaction safety.
    
    Args:
        user_id: User ID to regenerate tasks for
        days_threshold: Number of days after which a task is considered stale
        limit: Maximum number of tasks to regenerate
        batch_size: Size of batches for processing
        
    Returns:
        Dict with status and regenerated tasks
    """
    from app.models.task import Task
    from app.utils.task_generator import generate_replacement_task
    from app.models.user import User
    
    result = {
        'success': True,
        'tasks_regenerated': 0,
        'new_tasks': [],
        'error': None
    }
    
    # Get the user object
    user = User.query.get(user_id)
    if not user:
        result['success'] = False
        result['error'] = f"User with ID {user_id} not found"
        return result
    
    try:
        # Calculate threshold date
        threshold_date = datetime.utcnow() - timedelta(days=days_threshold)
        
        # Create query for stale tasks
        stale_tasks_query = Task.query.filter(
            Task.user_id == user_id,
            Task.last_updated <= threshold_date,
            Task.completed == False
        ).limit(limit)
        
        # Use our batch processing utility for database operations
        def process_batch(batch):
            batch_new_tasks = []
            stale_ids = []
            
            # First collect all the subject IDs and task IDs
            for stale_task in batch:
                stale_ids.append(stale_task.id)
            
            # Delete the stale tasks in a single operation
            if stale_ids:
                db.session.query(Task).filter(Task.id.in_(stale_ids)).delete(synchronize_session=False)
            
            # Now generate replacement tasks
            for stale_task in batch:
                subject_id = stale_task.subject_id
                new_task = generate_replacement_task(user, subject_id)
                if new_task:
                    batch_new_tasks.append(new_task)
            
            return batch_new_tasks
        
        # Process in batches
        new_tasks = db_batch_process(
            stale_tasks_query, 
            batch_size=batch_size,
            process_func=process_batch
        )
        
        result['tasks_regenerated'] = len(new_tasks)
        result['new_tasks'] = new_tasks
        
    except Exception as e:
        db.session.rollback()
        result['success'] = False
        result['error'] = str(e)
        current_app.logger.error(f"Error regenerating stale tasks: {str(e)}")
    
    return result

def update_task_priorities(user_id, batch_size=50):
    """
    Update task priorities based on due dates and importance.
    Uses batch processing for efficiency.
    
    Args:
        user_id: User ID to update task priorities for
        batch_size: Size of batches for processing
        
    Returns:
        Number of tasks updated
    """
    from app.models.task import Task
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    tomorrow = now + timedelta(days=1)
    next_week = now + timedelta(days=7)
    
    # Get all incomplete tasks for the user
    tasks_query = Task.query.filter(
        Task.user_id == user_id,
        Task.completed == False
    )
    
    # Update function to apply to each task
    def update_priority(task):
        # Calculate base priority based on due date
        if task.due_date:
            if task.due_date <= tomorrow:
                # Due today or tomorrow
                task.priority = min(100, task.priority + 30)
            elif task.due_date <= next_week:
                # Due within a week
                task.priority = min(90, task.priority + 20)
            else:
                # Due later
                task.priority = max(50, task.priority)
        
        # Factor in importance
        if task.importance >= 4:  # High importance
            task.priority = min(100, task.priority + 15)
        elif task.importance <= 2:  # Low importance
            task.priority = max(10, task.priority - 10)
        
        # Update last_updated timestamp
        task.last_updated = datetime.utcnow()
    
    # Process in batches
    updated_count = 0
    try:
        # Use our batch processing utility
        def process_priority_batch(batch):
            for task in batch:
                update_priority(task)
            return len(batch)
        
        batch_results = db_batch_process(
            tasks_query,
            batch_size=batch_size,
            process_func=process_priority_batch
        )
        
        updated_count = sum(batch_results)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating task priorities: {str(e)}")
    
    return updated_count
