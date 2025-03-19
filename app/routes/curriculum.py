from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models.curriculum import Subject, Topic, Subtopic

# Create a blueprint for curriculum routes
curriculum = Blueprint('curriculum', __name__)

@curriculum.route('/')
@login_required
def view_curriculum():
    """Curriculum browser view."""
    # Get all subjects
    subjects = Subject.query.all()
    return render_template('curriculum/index.html', subjects=subjects)

@curriculum.route('/api/subjects')
@login_required
def get_subjects():
    """API endpoint to get all subjects."""
    subjects = Subject.query.all()
    return jsonify({
        'subjects': [
            {
                'id': subject.id,
                'title': subject.title,
                'description': subject.description,
                'topic_count': len(subject.topics)
            }
            for subject in subjects
        ]
    })

@curriculum.route('/api/subject/<int:subject_id>/topics')
@login_required
def get_topics(subject_id):
    """API endpoint to get topics for a subject."""
    topics = Topic.query.filter_by(subject_id=subject_id).all()
    
    if not topics:
        return jsonify({'topics': []})
    
    return jsonify({
        'topics': [
            {
                'id': topic.id,
                'name': topic.name,
                'title': topic.title,
                'description': topic.description,
                'subtopics_count': len(topic.subtopics)
            }
            for topic in topics
        ]
    })

@curriculum.route('/api/topic/<int:topic_id>/subtopics')
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

@curriculum.route('/api/curriculum/search')
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
