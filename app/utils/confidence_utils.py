from app import db
from app.models.confidence import SubtopicConfidence, TopicConfidence

def update_subtopic_confidence(user_id, subtopic_id, confidence_level, priority=False):
    """
    Update a user's confidence level for a specific subtopic.
    
    Args:
        user_id (int): User ID
        subtopic_id (int): Subtopic ID
        confidence_level (int): New confidence level (1-5)
        priority (bool): Whether this subtopic is marked as priority
        
    Returns:
        bool: Success status
    """
    try:
        # Get or create confidence entry
        confidence = SubtopicConfidence.query.filter_by(
            user_id=user_id,
            subtopic_id=subtopic_id
        ).first()
        
        if not confidence:
            # Create new entry if it doesn't exist
            confidence = SubtopicConfidence(
                user_id=user_id,
                subtopic_id=subtopic_id,
                confidence_level=confidence_level,
                priority=priority
            )
            db.session.add(confidence)
        else:
            # Update existing entry
            confidence.confidence_level = confidence_level
            confidence.priority = priority
        
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error updating subtopic confidence: {e}")
        db.session.rollback()
        return False

def update_subtopics_confidence_from_dict(user_id, confidence_dict):
    """
    Update confidence levels for multiple subtopics at once.
    
    Args:
        user_id (int): User ID
        confidence_dict (dict): Dictionary of {subtopic_id: (confidence_level, priority)}
        
    Returns:
        bool: Success status
    """
    try:
        # Update each subtopic confidence
        for subtopic_id, (confidence_level, priority) in confidence_dict.items():
            # Get or create confidence entry
            confidence = SubtopicConfidence.query.filter_by(
                user_id=user_id,
                subtopic_id=subtopic_id
            ).first()
            
            if not confidence:
                # Create new entry if it doesn't exist
                confidence = SubtopicConfidence(
                    user_id=user_id,
                    subtopic_id=subtopic_id,
                    confidence_level=confidence_level,
                    priority=priority
                )
                db.session.add(confidence)
            else:
                # Update existing entry
                confidence.confidence_level = confidence_level
                confidence.priority = priority
        
        # Commit all changes
        db.session.commit()
        
        # Update topic confidences for affected topics
        from app.models.curriculum import Subtopic
        affected_topics = set()
        
        for subtopic_id in confidence_dict.keys():
            subtopic = Subtopic.query.get(subtopic_id)
            if subtopic:
                affected_topics.add(subtopic.topic_id)
        
        for topic_id in affected_topics:
            TopicConfidence.update_for_topic(topic_id, user_id)
        
        return True
    except Exception as e:
        print(f"Error updating multiple subtopic confidences: {e}")
        db.session.rollback()
        return False

def update_topic_confidence(user_id, topic_id):
    """
    Update confidence percentage for a topic based on its subtopics.
    
    Args:
        user_id (int): User ID
        topic_id (int): Topic ID
        
    Returns:
        float: The updated confidence percentage (0-100)
    """
    try:
        # Calculate and update topic confidence
        topic_confidence = TopicConfidence.update_for_topic(topic_id, user_id)
        return topic_confidence.confidence_percent
    except Exception as e:
        print(f"Error updating topic confidence: {e}")
        return 50.0  # Default to 50% on error 