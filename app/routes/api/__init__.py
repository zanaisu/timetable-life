from flask import Blueprint, jsonify, request, current_app, send_from_directory
import os
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models.task import Task, TaskSubtopic, TaskType
from app.models.curriculum import Subtopic, Topic
from app.utils.task_generator import generate_replacement_task
from app.routes.api.curriculum import curriculum_bp
from app.routes.api.confidence import confidence_bp
from app.models.confidence import SubtopicConfidence
from app.utils.confidence_utils import update_subtopics_confidence_from_dict

# Create blueprint
api_bp = Blueprint('api', __name__)

# Register blueprints with API
# api_bp.register_blueprint(curriculum_bp)  # Comment this out to avoid double registration
api_bp.register_blueprint(confidence_bp)

@api_bp.route('/tasks/complete/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    """Mark a task as completed."""
    task = Task.query.get_or_404(task_id)
    
    # Ensure the task belongs to the current user
    if task.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Mark task as completed
    task.mark_completed()
    db.session.commit()
    
    # Get subtopics in this task for confidence prompt
    subtopics = []
    for task_subtopic in task.subtopics:
        subtopic = Subtopic.query.get(task_subtopic.subtopic_id)
        if subtopic:
            # Get current confidence
            confidence = SubtopicConfidence.query.filter_by(
                user_id=current_user.id,
                subtopic_id=subtopic.id
            ).first()
            
            confidence_level = confidence.confidence_level if confidence else 3
            priority = confidence.priority if confidence else False
            
            subtopics.append({
                'id': subtopic.id,
                'title': subtopic.title,
                'confidence': confidence_level,
                'priority': priority
            })
    
    return jsonify({
        'success': True,
        'message': 'Task marked as completed',
        'subtopics': subtopics
    })

@api_bp.route('/tasks/skip/<int:task_id>', methods=['POST'])
@login_required
def skip_task(task_id):
    """Skip a task and generate a replacement task."""
    task = Task.query.get_or_404(task_id)
    
    # Ensure the task belongs to the current user
    if task.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Get subtopics in this task for confidence prompt before skipping
    subtopics = []
    for task_subtopic in task.subtopics:
        subtopic = Subtopic.query.get(task_subtopic.subtopic_id)
        if subtopic:
            # Get current confidence
            confidence = SubtopicConfidence.query.filter_by(
                user_id=current_user.id,
                subtopic_id=subtopic.id
            ).first()
            
            confidence_level = confidence.confidence_level if confidence else 3
            priority = confidence.priority if confidence else False
            
            subtopics.append({
                'id': subtopic.id,
                'title': subtopic.title,
                'confidence': confidence_level,
                'priority': priority
            })
    
    # Get subject ID for generating replacement
    subject_id = task.subject_id
    
    # Mark task as skipped
    task.mark_skipped()
    
    # Generate a replacement task
    new_task = generate_replacement_task(current_user, subject_id)
    
    if not new_task:
        return jsonify({
            'success': False,
            'message': 'Failed to generate replacement task'
        }), 500
    
    # Format task data for response
    task_data = {
        'id': new_task.id,
        'title': new_task.title,
        'description': new_task.description,
        'duration': new_task.total_duration,
        'subject': {
            'id': new_task.subject_id,
            'title': new_task.subject.title
        },
        'task_type': {
            'id': new_task.task_type_id,
            'name': new_task.task_type.name
        }
    }
    
    return jsonify({
        'success': True,
        'message': 'Task skipped and replacement generated',
        'task': task_data,
        'subtopics': subtopics
    })

@api_bp.route('/tasks/refresh', methods=['POST'])
@login_required
def refresh_tasks():
    """Regenerate all tasks for today."""
    today = datetime.utcnow().date()
    
    # Get all active tasks for today
    active_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.due_date == today,
        Task.completed_at.is_(None),
        Task.skipped_at.is_(None)
    ).all()
    
    # Mark all as skipped
    for task in active_tasks:
        task.mark_skipped()
    
    db.session.commit()
    
    try:
        # Always generate exactly 3 tasks - one for each main subject category
        # This ensures balanced coverage across Biology, Chemistry, and Psychology
        from app.utils.optimization_tasks import generate_balanced_task_batch
        tasks = generate_balanced_task_batch(current_user.id, count=3, max_per_subject=1)
        
        if not tasks:
            # Fallback if balanced task generation failed
            # Calculate how many tasks to create based on study hours
            study_hours = current_user.study_hours_per_day
            
            # Weekend adjustment
            if datetime.utcnow().weekday() >= 5:  # 5=Saturday, 6=Sunday
                study_hours = current_user.weekend_study_hours
            
            # Approximately 1 task per 30 minutes of study time
            num_tasks = max(1, int(study_hours * 2))
            
            # Generate new tasks using old method
            tasks = []
            for _ in range(num_tasks):
                task = generate_replacement_task(current_user)
                if task:
                    tasks.append(task)
        
        # Format tasks for the API response
        new_tasks = []
        for task in tasks:
            new_tasks.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'duration': task.total_duration,
                'subject': {
                    'id': task.subject_id,
                    'title': task.subject.title
                },
                'task_type': {
                    'id': task.task_type_id,
                    'name': task.task_type.name
                }
            })
        
        return jsonify({
            'success': True,
            'message': f'Generated {len(new_tasks)} new tasks',
            'tasks': new_tasks
        })
    except Exception as e:
        current_app.logger.error(f"Error in refresh_tasks: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error generating tasks: {str(e)}',
            'tasks': []
        }), 500

@api_bp.route('/tasks/add_bonus', methods=['POST'])
@login_required
def add_bonus_task():
    """Add an additional task."""
    # Get subject ID from request if provided
    subject_id = request.json.get('subject_id') if request.is_json else None
    
    # Generate a new task
    task = generate_replacement_task(current_user, subject_id)
    
    if not task:
        return jsonify({
            'success': False,
            'message': 'Failed to generate bonus task'
        }), 500
    
    # Format task data for response
    task_data = {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'duration': task.total_duration,
        'subject': {
            'id': task.subject_id,
            'title': task.subject.title
        },
        'task_type': {
            'id': task.task_type_id,
            'name': task.task_type.name
        }
    }
    
    return jsonify({
        'success': True,
        'message': 'Bonus task added',
        'task': task_data
    })

@api_bp.route('/tasks/add_for_subtopic', methods=['POST'])
@login_required
def add_task_for_subtopic():
    """Add a task for a specific subtopic."""
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid request format'}), 400
    
    subtopic_id = request.json.get('subtopic_id')
    if not subtopic_id:
        return jsonify({'success': False, 'message': 'No subtopic ID provided'}), 400
    
    # Get the subtopic
    subtopic = Subtopic.query.get_or_404(subtopic_id)
    
    # Get the subject
    subject = subtopic.get_subject()
    
    # Get task type (default to notes)
    task_type_id = request.json.get('task_type_id')
    if not task_type_id:
        task_type = TaskType.query.filter_by(name='notes').first()
        if not task_type:
            task_type = TaskType.query.first()  # Fallback to any task type
    else:
        task_type = TaskType.query.get(task_type_id)
    
    if not task_type:
        return jsonify({'success': False, 'message': 'No task type available'}), 500
    
    # Create a task for this subtopic
    task = Task(
        user_id=current_user.id,
        subject_id=subject.id,
        task_type_id=task_type.id,
        due_date=datetime.utcnow().date(),
        title=f"{task_type.name.capitalize()} task: {subtopic.title}",
        description=f"Study the {subtopic.title} subtopic from {subject.title}.",
        total_duration=subtopic.estimated_duration or 30,  # Default to 30 minutes if not specified
    )
    
    db.session.add(task)
    
    # Link the task to the subtopic
    task_subtopic = TaskSubtopic(
        task_id=task.id,
        subtopic_id=subtopic.id
    )
    db.session.add(task_subtopic)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Task created for subtopic',
        'task': {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'duration': task.total_duration,
            'subject': {
                'id': subject.id,
                'title': subject.title
            },
            'task_type': {
                'id': task_type.id,
                'name': task_type.name
            }
        }
    })

@api_bp.route('/tasks/practice_subtopic', methods=['POST'])
@login_required
def practice_subtopic():
    """Create a practice session for a specific subtopic."""
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid request format'}), 400
    
    subtopic_id = request.json.get('subtopic_id')
    if not subtopic_id:
        return jsonify({'success': False, 'message': 'No subtopic ID provided'}), 400
    
    # Get the subtopic
    subtopic = Subtopic.query.get_or_404(subtopic_id)
    
    # Get the practice task type
    practice_type = TaskType.query.filter_by(name='practice').first()
    if not practice_type:
        return jsonify({'success': False, 'message': 'Practice task type not found'}), 500
    
    # Create a practice session ID
    session_id = f"practice_{subtopic_id}_{int(datetime.utcnow().timestamp())}"
    
    # Create a practice task
    task = Task(
        user_id=current_user.id,
        subject_id=subtopic.get_subject().id,
        task_type_id=practice_type.id,
        due_date=datetime.utcnow().date(),
        title=f"Practice: {subtopic.title}",
        description=f"Practice the {subtopic.title} subtopic.",
        total_duration=45,  # Default practice duration
        session_id=session_id
    )
    
    db.session.add(task)
    
    # Link the task to the subtopic
    task_subtopic = TaskSubtopic(
        task_id=task.id,
        subtopic_id=subtopic.id
    )
    db.session.add(task_subtopic)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Practice session created',
        'session_id': session_id,
        'task_id': task.id
    })

@api_bp.route('/tasks/start/<int:task_id>', methods=['POST'])
@login_required
def start_task(task_id):
    """Mark a task as in progress (for Pomodoro timer)."""
    task = Task.query.get_or_404(task_id)
    
    # Ensure the task belongs to the current user
    if task.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Mark task as in progress (if we add this field to the model in the future)
    # For now we'll just note the start without changing the model
    
    return jsonify({
        'success': True,
        'message': 'Task marked as in progress',
        'task_id': task_id
    })

@api_bp.route('/pomodoro/stats', methods=['GET'])
@login_required
def get_pomodoro_stats():
    """Get statistics for the Pomodoro dashboard."""
    # Calculate completion rate for last 7 days
    today = datetime.utcnow().date()
    seven_days_ago = today - timedelta(days=7)
    
    total_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.due_date >= seven_days_ago,
        Task.due_date <= today
    ).count()
    
    completed_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.due_date >= seven_days_ago,
        Task.due_date <= today,
        Task.completed_at.isnot(None)
    ).count()
    
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    return jsonify({
        'success': True,
        'stats': {
            'completion_rate': completion_rate,
            'total_pomodoros': 0,  # This would be stored in a new model if implemented
            'focus_time': 0        # This would be stored in a new model if implemented
        }
    })

@api_bp.route('/update-dark-mode', methods=['POST'])
@login_required
def update_dark_mode():
    """Toggle dark mode setting."""
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid request format'}), 400
    
    dark_mode = request.json.get('dark_mode', False)
    
    # Update user preference
    current_user.dark_mode = dark_mode
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Dark mode {"enabled" if dark_mode else "disabled"}',
        'dark_mode': dark_mode
    })

@api_bp.route('/subtopics/update_confidence', methods=['POST'])
@login_required
def update_subtopic_confidence():
    """Update confidence for subtopics."""
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid request format'}), 400
    
    subtopic_data = request.json.get('subtopics', {})
    
    if not subtopic_data:
        return jsonify({'success': False, 'message': 'No subtopic data provided'}), 400
    
    # Log the incoming data
    print(f"Updating confidence for subtopics: {subtopic_data}")
    
    # Format for update function
    formatted_data = {}
    
    for subtopic_id, data in subtopic_data.items():
        confidence_level = data.get('confidence')
        priority = data.get('priority', False)
        
        if confidence_level and 1 <= confidence_level <= 5:
            formatted_data[int(subtopic_id)] = (confidence_level, priority)
    
    # Update confidences
    success = update_subtopics_confidence_from_dict(current_user.id, formatted_data)
    
    if not success:
        return jsonify({'success': False, 'message': 'Error updating confidences'}), 500
    
    return jsonify({
        'success': True,
        'message': f'Updated {len(formatted_data)} subtopic confidences'
    })
