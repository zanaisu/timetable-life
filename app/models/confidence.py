from datetime import datetime
from app import db

class SubtopicConfidence(db.Model):
    """Model representing a user's confidence level for a specific subtopic."""
    __tablename__ = 'subtopic_confidences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subtopic_id = db.Column(db.Integer, db.ForeignKey('subtopics.id'), nullable=False)
    confidence_level = db.Column(db.Integer, default=3)  # Default to 3 out of 5
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    priority = db.Column(db.Boolean, default=False)  # Whether this subtopic is marked as priority
    
    # Using back_populates instead of backref per best practices
    user = db.relationship('User', back_populates='subtopic_confidences', lazy=True)
    subtopic = db.relationship('Subtopic', back_populates='subtopic_confidences', lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'subtopic_id', name='unique_user_subtopic_confidence'),
    )
    
    def __repr__(self):
        return f"<SubtopicConfidence user_id={self.user_id} subtopic_id={self.subtopic_id} level={self.confidence_level}>"
    
    @staticmethod
    def get_or_create(user_id, subtopic_id, default_level=3):
        """Get existing confidence or create new one with default level."""
        confidence = SubtopicConfidence.query.filter_by(
            user_id=user_id, 
            subtopic_id=subtopic_id
        ).first()
        
        if not confidence:
            confidence = SubtopicConfidence(
                user_id=user_id,
                subtopic_id=subtopic_id,
                confidence_level=default_level
            )
            db.session.add(confidence)
            db.session.commit()
            
        return confidence
    
    def calculate_weight(self):
        """Calculate priority weight using formula: (7 - confidence_level)²"""
        return (7 - self.confidence_level) ** 2
    
    def set_priority(self, priority_value):
        """Set or unset the priority flag."""
        self.priority = bool(priority_value)
        self.last_updated = datetime.utcnow()

class TopicConfidence(db.Model):
    """Model representing a user's confidence level for a specific topic."""
    __tablename__ = 'topic_confidences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    confidence_percent = db.Column(db.Float, default=50.0)  # Default to 50%
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Using back_populates instead of backref per best practices
    user = db.relationship('User', back_populates='topic_confidences', lazy=True)
    topic = db.relationship('Topic', back_populates='topic_confidences', lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'topic_id', name='unique_user_topic_confidence'),
    )
    
    def __repr__(self):
        return f"<TopicConfidence user_id={self.user_id} topic_id={self.topic_id} percent={self.confidence_percent}>"
    
    @staticmethod
    def get_or_create(user_id, topic_id, default_percent=50.0):
        """Get existing confidence or create new one with default level."""
        confidence = TopicConfidence.query.filter_by(
            user_id=user_id, 
            topic_id=topic_id
        ).first()
        
        if not confidence:
            confidence = TopicConfidence(
                user_id=user_id,
                topic_id=topic_id,
                confidence_percent=default_percent
            )
            db.session.add(confidence)
            db.session.commit()
            
        return confidence
    
    @staticmethod
    def calculate_for_topic(topic_id, user_id):
        """Calculate topic confidence as mean of subtopic confidences."""
        from app.models.curriculum import Subtopic
        
        # Get all subtopics for this topic
        subtopics = Subtopic.query.filter_by(topic_id=topic_id).all()
        
        # Handle empty subtopics case
        if not subtopics:
            return 0.0
        
        # Get confidence levels for these subtopics
        subtopic_confidences = SubtopicConfidence.query.filter_by(
            user_id=user_id
        ).filter(
            SubtopicConfidence.subtopic_id.in_([st.id for st in subtopics])
        ).all()
        
        # If no confidence records exist, create them with default values
        if not subtopic_confidences or len(subtopic_confidences) < len(subtopics):
            for subtopic in subtopics:
                SubtopicConfidence.get_or_create(user_id, subtopic.id)
                
            # Refresh the confidence records
            subtopic_confidences = SubtopicConfidence.query.filter_by(
                user_id=user_id
            ).filter(
                SubtopicConfidence.subtopic_id.in_([st.id for st in subtopics])
            ).all()
        
        # Calculate mean confidence
        total_confidence = sum(sc.confidence_level for sc in subtopic_confidences)
        count = len(subtopic_confidences)
        
        # Avoid division by zero
        if count == 0:
            return 50.0
            
        avg_confidence = total_confidence / count
        
        # Convert to percentage with adjusted scale where:
        # 1/5 = 0%, 3/5 = 50%, 5/5 = 100%
        confidence_percent = ((avg_confidence - 1) / 4.0) * 100.0
        
        return confidence_percent
    
    @staticmethod
    def update_for_topic(topic_id, user_id):
        """Update confidence percentage for a topic."""
        # Calculate new confidence percentage
        confidence_percent = TopicConfidence.calculate_for_topic(topic_id, user_id)
        
        # Get or create topic confidence record
        topic_confidence = TopicConfidence.get_or_create(user_id, topic_id)
        
        # Update the percentage
        topic_confidence.confidence_percent = confidence_percent
        topic_confidence.last_updated = datetime.utcnow()
        
        db.session.commit()
        
        return topic_confidence
