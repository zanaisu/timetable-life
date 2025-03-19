from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.curriculum import Subject, Topic, Subtopic

# Create API blueprint for curriculum
curriculum_bp = Blueprint('curriculum_api', __name__, url_prefix='/api/curriculum')

@curriculum_bp.route('/subjects')
@login_required
def get_subjects():
    """API endpoint to get all subjects."""
    subjects = Subject.query.all()
    
    # Filter out duplicates based on course codes
    unique_subjects = {}
    
    # First, sort subjects by priority - subjects with course codes first
    subjects_with_codes = []
    generic_subjects = []
    
    for subject in subjects:
        if '(' in subject.title and ')' in subject.title:
            subjects_with_codes.append(subject)
        else:
            generic_subjects.append(subject)
    
    # Process subjects with course codes first
    for subject in subjects_with_codes:
        code_part = subject.title.split('(')[-1].split(')')[0]
        if code_part:
            course_code = code_part
            # Check if title contains year information
            year_info = None
            if "Year 12" in subject.title:
                year_info = "Year 12"
            elif "Year 13" in subject.title:
                year_info = "Year 13"
            
            # Create a composite key that includes year information if available
            composite_key = course_code
            if year_info:
                composite_key = f"{course_code}_{year_info}"
            
            # Store by composite key to preserve year distinction
            if composite_key not in unique_subjects:
                unique_subjects[composite_key] = subject
    
    # Then process generic subjects, only add if base name doesn't exist
    for subject in generic_subjects:
        base_name = subject.title.lower().strip()
        
        # Check if this is a generic version of a subject we already have
        should_add = True
        for key, existing_subject in unique_subjects.items():
            if base_name in existing_subject.title.lower():
                # This is a generic version of a subject we already have
                should_add = False
                break
        
        if should_add:
            # Only add if not a duplicate
            unique_subjects[base_name] = subject
    
    # Use the filtered list
    filtered_subjects = list(unique_subjects.values())
    
    return jsonify({
        'subjects': [
            {
                'id': subject.id,
                'title': subject.title,
                'description': subject.description,
                'topic_count': len(subject.topics)
            }
            for subject in filtered_subjects
        ]
    })

@curriculum_bp.route('/subject/<int:subject_id>/topics')
@login_required
def get_topics(subject_id):
    """API endpoint to get topics for a subject."""
    topics = Topic.query.filter_by(subject_id=subject_id).all()
    
    if not topics:
        return jsonify({'topics': []})
    
    # Get the subject title
    subject = Subject.query.get(subject_id)
    
    # Filter out specific Psychology topics with 0 subtopics
    if subject and subject.title == "Psychology":
        topics = [topic for topic in topics if topic.title not in [
            "Introductory Topics in Psychology - 0 subtopics",
            "Psychology in Context - 0 subtopics",
            "Issues and Options in Psychology - 0 subtopics"
        ]]
    
    result = []
    for topic in topics:        
        result.append({
            'id': topic.id,
            'name': topic.name,
            'title': topic.title,
            'description': topic.description,
            'subtopics_count': len(topic.subtopics)
        })
    
    return jsonify({'topics': result})

@curriculum_bp.route('/topic/<int:topic_id>/subtopics')
@login_required
def get_subtopics(topic_id):
    """API endpoint to get subtopics for a topic."""
    subtopics = Subtopic.query.filter_by(topic_id=topic_id).all()
    
    if not subtopics:
        return jsonify({'subtopics': []})
    
    result = []
    for subtopic in subtopics:
        result.append({
            'id': subtopic.id,
            'title': subtopic.title,
            'description': subtopic.description,
            'estimated_duration': subtopic.estimated_duration
        })
    
    return jsonify({'subtopics': result})

@curriculum_bp.route('/search')
@login_required
def search_curriculum():
    """API endpoint for curriculum search."""
    query = request.args.get('q', '').lower()
    if not query or len(query) < 2:
        return jsonify({'results': []})
    
    # Search subjects
    subjects = Subject.query.filter(Subject.title.ilike(f'%{query}%')).all()
    
    # Search topics
    topics = Topic.query.filter(Topic.title.ilike(f'%{query}%')).all()
    
    # Search subtopics
    subtopics = Subtopic.query.filter(Subtopic.title.ilike(f'%{query}%')).all()
    
    results = {
        'subjects': [{'id': s.id, 'title': s.title} for s in subjects],
        'topics': [{'id': t.id, 'title': t.title, 'subject_id': t.subject_id} for t in topics],
        'subtopics': [{'id': st.id, 'title': st.title, 'topic_id': st.topic_id} for st in subtopics]
    }
    
    return jsonify({'results': results})

# Removed all confidence-related endpoints
