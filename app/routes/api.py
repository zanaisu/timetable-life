from flask import Blueprint, jsonify, request, current_app, send_from_directory, render_template, session
import os
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models.task import Task, TaskSubtopic, TaskType
from app.models.curriculum import Subtopic, Topic, Subject
from app.models.confidence import SubtopicConfidence, TopicConfidence
from app.utils.confidence_utils import update_subtopic_confidence, update_subtopics_confidence_from_dict, update_topic_confidence as update_topic_conf_util
from app.utils.task_generator import generate_replacement_task, generate_task_for_subject
from app.utils.analytics_utils import ConfidenceAnalytics
from app.utils.optimization_tasks import generate_balanced_task_batch
from app.utils.task_generator_main import generate_task_for_subject

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

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
    
    # Set confidence prompt flag
    task.confidence_prompt_shown = True
    db.session.commit()
    
    # Get subtopics in this task for confidence prompt
    subtopics = []
    
    # Get all the task's subtopics
    if not task.subtopics or len(task.subtopics) == 0:
        print(f"Task {task_id} has no subtopics associated with it")
    
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
    
    # Log what's being returned
    if subtopics:
        print(f"Returning {len(subtopics)} subtopics for task {task_id}")
    else:
        print(f"No subtopics found for task {task_id}")
    
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
        'task': task_data
    })

@api_bp.route('/tasks/refresh', methods=['POST'])
@login_required
def refresh_tasks():
    """Regenerate all tasks for today with improved variety."""
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
    
    # Calculate study hours
    study_hours = current_user.study_hours_per_day
    
    # Weekend adjustment
    if datetime.utcnow().weekday() >= 5:  # 5=Saturday, 6=Sunday
        study_hours = current_user.weekend_study_hours
        
    # Get all completed tasks from today to avoid repeating
    completed_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.due_date == today,
        Task.completed_at.isnot(None)
    ).all()
    
    completed_subject_ids = [task.subject_id for task in completed_tasks]
    
    # Get all available subjects
    all_subjects = Subject.query.all()
    
    # Prefer subjects that haven't been completed today
    available_subjects = [s for s in all_subjects if s.id not in completed_subject_ids]
    
    # If we've completed tasks for all subjects today, use all subjects
    if not available_subjects:
        available_subjects = all_subjects
    
    # If we have more than 3 subjects, randomly pick 3 different ones
    random.shuffle(available_subjects)
    subject_sample = available_subjects[:min(3, len(available_subjects))]
    
    # Always generate exactly 3 tasks - one for each main subject category
    # But now we're more careful about which subjects to use
    from app.utils.optimization_tasks import generate_balanced_task_batch
    from app.utils.task_generator import generate_task_for_subject
    
    # Try to generate tasks for each selected subject
    new_tasks = []
    
    for subject in subject_sample:
        task = generate_task_for_subject(current_user, subject.id)
        if task:
            new_tasks.append(task)
    
    # If we don't have enough tasks, fall back to the original balanced approach
    if len(new_tasks) < min(3, len(all_subjects)):
        # Clear the tasks we've generated so far
        for task in new_tasks:
            db.session.delete(task)
        db.session.commit()
        
        # Use balanced task generation as a fallback
        new_tasks = generate_balanced_task_batch(current_user.id, count=3, max_per_subject=1)
    
    # Format tasks for the API response
    formatted_tasks = []
    for task in new_tasks:
        formatted_tasks.append({
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
        'message': f'Generated {len(formatted_tasks)} new tasks',
        'tasks': formatted_tasks
    })

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

@api_bp.route('/topic-confidence/<int:topic_id>', methods=['POST'])
@login_required
def update_topic_confidence(topic_id):
    """Update confidence for a topic."""
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid request format'}), 400
    
    new_level = request.json.get('confidence_level')
    
    if not new_level or not 1 <= new_level <= 5:
        return jsonify({'success': False, 'message': 'Invalid confidence level'}), 400
    
    # Get the topic
    topic = Topic.query.get_or_404(topic_id)
    
    # Get all subtopics for this topic
    subtopics = Subtopic.query.filter_by(topic_id=topic_id).all()
    
    if not subtopics:
        return jsonify({
            'success': False, 
            'message': 'Cannot set topic confidence directly. Topic has no subtopics.'
        }), 400
    
    # Update all subtopic confidences to this level first
    for subtopic in subtopics:
        # Find or create confidence entry for each subtopic
        subtopic_confidence = SubtopicConfidence.query.filter_by(
            user_id=current_user.id,
            subtopic_id=subtopic.id
        ).first()
        
        if not subtopic_confidence:
            subtopic_confidence = SubtopicConfidence(
                user_id=current_user.id,
                subtopic_id=subtopic.id,
                confidence_level=new_level  # Use the direct value (1-5 scale)
            )
            db.session.add(subtopic_confidence)
        else:
            subtopic_confidence.update_confidence(new_level)
    
    db.session.commit()
    
    # Now calculate and update the topic confidence based on these subtopics
    confidence_level = update_topic_conf_util(current_user.id, topic_id)
    
    return jsonify({
        'success': True,
        'message': 'Topic confidence updated via subtopic updates',
        'topic_id': topic_id,
        'confidence_level': new_level  # Return the original 1-5 scale value to frontend
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

@api_bp.route('/subtopics/priority/<int:subtopic_id>', methods=['POST'])
@login_required
def set_subtopic_priority(subtopic_id):
    """Set priority for a subtopic."""
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid request format'}), 400
    
    priority = request.json.get('priority', False)
    
    # Get the subtopic
    subtopic = Subtopic.query.get_or_404(subtopic_id)
    
    # Find or create confidence entry
    confidence = SubtopicConfidence.query.filter_by(
        user_id=current_user.id,
        subtopic_id=subtopic_id
    ).first()
    
    if confidence:
        confidence.set_priority(priority)
    else:
        subtopic_key = subtopic.generate_subtopic_key()
        confidence = SubtopicConfidence(
            user_id=current_user.id,
            subtopic_id=subtopic_id,
            subtopic_key=subtopic_key,
            confidence_level=3,  # Default
            priority=priority
        )
        db.session.add(confidence)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Subtopic priority {"set" if priority else "unset"}',
        'subtopic_id': subtopic_id,
        'priority': priority
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
    # Get task completion rate
    analytics = ConfidenceAnalytics(current_user.id)
    
    # Calculate completion rate for last 7 days
    today = datetime.utcnow().date()
    seven_days_ago = today - datetime.timedelta(days=7)
    
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
    
    # Get focus areas (priority subtopics)
    priority_subtopics = analytics.get_priority_recommendations(limit=3)
    
    return jsonify({
        'success': True,
        'stats': {
            'completion_rate': completion_rate,
            'total_pomodoros': 0,  # This would be stored in a new model if implemented
            'focus_time': 0,       # This would be stored in a new model if implemented
            'focus_areas': [
                {
                    'id': item['subtopic'].id,
                    'title': item['subtopic'].title,
                    'subject': item['subject'].title
                }
                for item in priority_subtopics
            ]
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

@api_bp.route('/curriculum/hierarchy', methods=['GET'])
@login_required
def get_curriculum_hierarchy():
    """Get the curriculum hierarchy for custom task creation."""
    # Get all subjects
    subjects = Subject.query.all()
    
    result = []
    for subject in subjects:
        subject_data = {
            'id': subject.id,
            'title': subject.title,
            'topics': []
        }
        
        # Get topics for this subject
        topics = Topic.query.filter_by(subject_id=subject.id).all()
        for topic in topics:
            topic_data = {
                'id': topic.id,
                'title': topic.title,
                'subtopics': []
            }
            
            # Get subtopics for this topic
            subtopics = Subtopic.query.filter_by(topic_id=topic.id).all()
            for subtopic in subtopics:
                topic_data['subtopics'].append({
                    'id': subtopic.id,
                    'title': subtopic.title,
                    'duration': subtopic.estimated_duration
                })
                
            subject_data['topics'].append(topic_data)
        
        result.append(subject_data)
        
    return jsonify({
        'success': True,
        'hierarchy': result
    })

@api_bp.route('/tasks/create_custom', methods=['POST'])
@login_required
def create_custom_task():
    """Create a custom task with selected subject, topic, and subtopics."""
    if not request.is_json:
        return jsonify({
            'success': False,
            'message': 'Invalid request format'
        }), 400
        
    data = request.json
    subject_id = data.get('subject_id')
    topic_id = data.get('topic_id')
    subtopic_ids = data.get('subtopic_ids', [])
    task_type_id = data.get('task_type_id')
    
    # Validate required fields
    if not subject_id or not topic_id or not subtopic_ids or not task_type_id:
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        }), 400
        
    try:
        # Get the subject and topic
        subject = Subject.query.get(subject_id)
        topic = Topic.query.get(topic_id)
        
        if not subject or not topic:
            return jsonify({
                'success': False,
                'message': 'Invalid subject or topic'
            }), 400
            
        # Create a new task
        new_task = Task(
            user_id=current_user.id,
            subject_id=subject_id,
            topic_id=topic_id,
            task_type_id=task_type_id,
            title=f"{subject.title}: {topic.title}",
            description=f"Custom task for {topic.title}",
            due_date=datetime.utcnow().date()
        )
        
        db.session.add(new_task)
        db.session.flush()  # Flush to get the new task ID
        
        # Add selected subtopics to the task
        total_duration = 0
        subtopic_titles = []
        
        for subtopic_id in subtopic_ids:
            subtopic = Subtopic.query.get(subtopic_id)
            if subtopic:
                # Add subtopic to task
                task_subtopic = TaskSubtopic(
                    task_id=new_task.id,
                    subtopic_id=subtopic_id,
                    duration=subtopic.estimated_duration
                )
                db.session.add(task_subtopic)
                
                total_duration += subtopic.estimated_duration
                subtopic_titles.append(subtopic.title)
        
        # Update task description and duration
        new_task.description = f"Custom task covering: {', '.join(subtopic_titles)}"
        new_task.total_duration = total_duration
        
        db.session.commit()
        
        # Format task data for response
        task_data = {
            'id': new_task.id,
            'title': new_task.title,
            'description': new_task.description,
            'duration': new_task.total_duration,
            'subject': {
                'id': subject.id,
                'title': subject.title
            },
            'task_type': {
                'id': new_task.task_type_id,
                'name': new_task.task_type.name
            }
        }
        
        return jsonify({
            'success': True,
            'message': 'Custom task created',
            'task': task_data
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creating task: {str(e)}'
        }), 500

@api_bp.route('/task_types', methods=['GET'])
@login_required
def get_task_types():
    """Get all task types."""
    task_types = TaskType.query.all()
    
    result = []
    for task_type in task_types:
        result.append({
            'id': task_type.id,
            'name': task_type.name,
            'description': task_type.description
        })
        
    return jsonify({
        'success': True,
        'task_types': result
    })
