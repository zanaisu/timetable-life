from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.confidence import SubtopicConfidence, TopicConfidence
from app.models.curriculum import Subtopic, Topic
from datetime import datetime

# Create blueprint for confidence API
confidence_bp = Blueprint('confidence_api', __name__, url_prefix='/confidence')

@confidence_bp.route('/user/data', methods=['GET'])
@login_required
def get_all_confidence_data():
    """Get all confidence data for the current user."""
    # Get all subtopic confidence data
    subtopic_confidences = SubtopicConfidence.query.filter_by(user_id=current_user.id).all()
    
    # Get all topic confidence data
    topic_confidences = TopicConfidence.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'subtopic_confidences': [
            {
                'subtopic_id': sc.subtopic_id,
                'confidence_level': sc.confidence_level,
                'last_updated': sc.last_updated.isoformat() if sc.last_updated else None
            }
            for sc in subtopic_confidences
        ],
        'topic_confidences': [
            {
                'topic_id': tc.topic_id,
                'confidence_percent': tc.confidence_percent,
                'last_updated': tc.last_updated.isoformat() if tc.last_updated else None
            }
            for tc in topic_confidences
        ]
    })

@confidence_bp.route('/user/subtopic/<int:subtopic_id>', methods=['GET', 'PUT'])
@login_required
def subtopic_confidence(subtopic_id):
    """Get or update confidence for a specific subtopic."""
    subtopic = Subtopic.query.get_or_404(subtopic_id)
    user_id = current_user.id
    
    if request.method == 'GET':
        confidence = SubtopicConfidence.query.filter_by(
            user_id=user_id, 
            subtopic_id=subtopic_id
        ).first()
        
        if not confidence:
            # Return default if not found
            return jsonify({
                'confidence_level': 3,
                'subtopic_id': subtopic_id,
                'user_id': user_id
            })
            
        return jsonify({
            'confidence_level': confidence.confidence_level,
            'subtopic_id': subtopic_id,
            'user_id': user_id,
            'last_updated': confidence.last_updated.isoformat() if confidence.last_updated else None
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        if not data or 'confidence_level' not in data:
            return jsonify({'error': 'Confidence level is required'}), 400
            
        confidence_level = int(data['confidence_level'])
        
        # Validate confidence level (1-5)
        if confidence_level < 1 or confidence_level > 5:
            return jsonify({'error': 'Confidence level must be between 1 and 5'}), 400
            
        # Get or create confidence record
        confidence = SubtopicConfidence.query.filter_by(
            user_id=user_id, 
            subtopic_id=subtopic_id
        ).first()
        
        if not confidence:
            confidence = SubtopicConfidence(
                user_id=user_id,
                subtopic_id=subtopic_id,
                confidence_level=confidence_level
            )
            db.session.add(confidence)
        else:
            confidence.confidence_level = confidence_level
            confidence.last_updated = datetime.utcnow()
        
        # Update topic confidence
        topic_confidence = TopicConfidence.update_for_topic(subtopic.topic_id, user_id)
        
        db.session.commit()
        
        return jsonify({
            'confidence_level': confidence.confidence_level,
            'subtopic_id': subtopic_id,
            'user_id': user_id,
            'last_updated': confidence.last_updated.isoformat(),
            'topic_id': subtopic.topic_id,
            'topic_confidence': {
                'confidence_percent': topic_confidence.confidence_percent,
                'last_updated': topic_confidence.last_updated.isoformat()
            }
        })

@confidence_bp.route('/user/topic/<int:topic_id>', methods=['GET'])
@login_required
def topic_confidence(topic_id):
    """Get confidence for a specific topic."""
    topic = Topic.query.get_or_404(topic_id)
    user_id = current_user.id
    
    confidence = TopicConfidence.query.filter_by(
        user_id=user_id, 
        topic_id=topic_id
    ).first()
    
    if not confidence:
        # Calculate and create if it doesn't exist
        confidence = TopicConfidence.update_for_topic(topic_id, user_id)
    
    return jsonify({
        'confidence_percent': confidence.confidence_percent,
        'topic_id': topic_id,
        'user_id': user_id,
        'last_updated': confidence.last_updated.isoformat() if confidence.last_updated else None
    })

@confidence_bp.route('/user/initialize', methods=['POST'])
@login_required
def initialize_confidence():
    """Initialize confidence data for all subjects, topics, and subtopics."""
    user_id = current_user.id
    
    # Get all subtopics
    subtopics = Subtopic.query.all()
    
    # Create default confidence for each subtopic
    for subtopic in subtopics:
        SubtopicConfidence.get_or_create(user_id, subtopic.id)
    
    # Get all topics
    topics = Topic.query.all()
    
    # Create topic confidence records
    for topic in topics:
        TopicConfidence.update_for_topic(topic.id, user_id)
    
    return jsonify({
        'success': True,
        'message': f'Initialized confidence data for {len(subtopics)} subtopics and {len(topics)} topics'
    })
