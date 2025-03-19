"""
Query optimization utilities for efficient database access.
Provides optimized query functions for better performance with large datasets.
"""

from datetime import datetime, timedelta
from sqlalchemy import text, func
from app import db
from app.models.curriculum import Subject, Topic, Subtopic
from app.utils.optimization_cache import cached

@cached(timeout_seconds=3600)  # Cache for 1 hour
def get_optimized_subject_distribution(user_id):
    """
    Optimized version of subject distribution calculation with caching.
    Uses efficient SQL queries instead of multiple Python iterations.
    
    Args:
        user_id: User ID to calculate distribution for
        
    Returns:
        Dictionary with subject_id: percentage pairs
    """
    # Get all subjects
    subjects = Subject.query.all()
    
    # Early return if no subjects
    if not subjects:
        return {}
        
    subject_ids = [s.id for s in subjects]
    
    # Get tasks from the past week with a single query
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Use SQL to count tasks per subject efficiently
    task_counts = db.session.execute(
        text("""
        SELECT subject_id, COUNT(*) as count
        FROM tasks
        WHERE user_id = :user_id AND created_at >= :week_ago
        GROUP BY subject_id
        """),
        {"user_id": user_id, "week_ago": week_ago}
    ).all()
    
    # Convert to dictionary for easier lookup
    counts_dict = {row[0]: row[1] for row in task_counts}
    total_tasks = sum(counts_dict.values())
    
    # Special handling for Biology subjects - count them as one subject for distribution
    biology_subjects = [s for s in subjects if "Biology" in s.title]
    non_biology_subjects = [s for s in subjects if "Biology" not in s.title]
    
    # Calculate distribution
    distribution = {}
    
    # Handle no previous tasks case
    if total_tasks == 0:
        # Calculate equal share based on *effective* number of subjects
        # Biology (Y12 and Y13) count as ONE subject for this calculation
        effective_subject_count = len(non_biology_subjects) + (1 if biology_subjects else 0)
        equal_share = 1.0 / effective_subject_count if effective_subject_count > 0 else 0
        
        # Handle Biology as one subject for distribution
        if biology_subjects:
            # Biology as a whole gets the same share as any other single subject
            biology_share = equal_share
            
            # Get topic counts with a single query
            if len(biology_subjects) > 1:
                # Multiple biology subjects
                subject_ids_str = ','.join(str(s.id) for s in biology_subjects)
                bio_topic_counts = db.session.execute(
                    text(f"""
                    SELECT subject_id, COUNT(*) as count
                    FROM topics
                    WHERE subject_id IN ({subject_ids_str})
                    GROUP BY subject_id
                    """)
                ).all()
            elif len(biology_subjects) == 1:
                # Single biology subject - don't use IN clause
                bio_topic_counts = db.session.execute(
                    text("""
                    SELECT subject_id, COUNT(*) as count
                    FROM topics
                    WHERE subject_id = :subject_id
                    GROUP BY subject_id
                    """),
                    {"subject_id": biology_subjects[0].id}
                ).all()
            else:
                # No biology subjects
                bio_topic_counts = []
            
            bio_topic_counts_dict = {row[0]: row[1] for row in bio_topic_counts}
            total_bio_topics = sum(bio_topic_counts_dict.values())
            
            if total_bio_topics > 0:
                for subject in biology_subjects:
                    topic_count = bio_topic_counts_dict.get(subject.id, 0)
                    # Safe division
                    distribution[subject.id] = biology_share * (topic_count / total_bio_topics) if total_bio_topics > 0 else 0
            else:
                # Equal split if no topic data
                for subject in biology_subjects:
                    distribution[subject.id] = biology_share / len(biology_subjects)
        
        # Assign share to other subjects
        for subject in non_biology_subjects:
            distribution[subject.id] = equal_share
    
    else:
        # Calculate inverse frequency for each subject
        inverse_frequency = {}
        
        # Handle Biology specially
        biology_subject_ids = [s.id for s in biology_subjects]
        if biology_subject_ids:
            # Calculate total biology tasks
            biology_count = sum(counts_dict.get(s_id, 0) for s_id in biology_subject_ids)
            bio_percentage = biology_count / total_tasks if total_tasks > 0 else 0
            
            # The less Biology appears, the more weight it should get
            bio_inverse = 1.0 - bio_percentage if bio_percentage > 0 else 1.0
            
            # Get topic counts for Biology subjects
            if len(biology_subject_ids) > 1:
                # Multiple biology subjects
                subject_ids_str = ','.join(str(s_id) for s_id in biology_subject_ids)
                bio_topic_counts = db.session.execute(
                    text(f"""
                    SELECT subject_id, COUNT(*) as count
                    FROM topics
                    WHERE subject_id IN ({subject_ids_str})
                    GROUP BY subject_id
                    """)
                ).all()
            elif len(biology_subject_ids) == 1:
                # Single biology subject - don't use IN clause
                bio_topic_counts = db.session.execute(
                    text("""
                    SELECT subject_id, COUNT(*) as count
                    FROM topics
                    WHERE subject_id = :subject_id
                    GROUP BY subject_id
                    """),
                    {"subject_id": biology_subject_ids[0]}
                ).all()
            else:
                # No biology subjects
                bio_topic_counts = []
            
            bio_topic_counts_dict = {row[0]: row[1] for row in bio_topic_counts}
            total_bio_topics = sum(bio_topic_counts_dict.values())
            
            if total_bio_topics > 0:
                for subject_id in biology_subject_ids:
                    topic_count = bio_topic_counts_dict.get(subject_id, 0)
                    inverse_frequency[subject_id] = bio_inverse * (topic_count / total_bio_topics)
            else:
                # Equal split if no topic data
                for subject_id in biology_subject_ids:
                    inverse_frequency[subject_id] = bio_inverse / len(biology_subject_ids)
        
        # Handle other subjects
        for subject in subjects:
            if "Biology" not in subject.title:
                subject_percentage = counts_dict.get(subject.id, 0) / total_tasks if total_tasks > 0 else 0
                inverse_frequency[subject.id] = 1.0 - subject_percentage if subject_percentage > 0 else 1.0
        
        # Normalize to make sum = 1.0
        total_inverse = sum(inverse_frequency.values())
        if total_inverse > 0:
            for subject_id, value in inverse_frequency.items():
                distribution[subject_id] = value / total_inverse
        else:
            # Fallback to equal distribution with safety check - use effective subject count
            effective_subject_count = len(non_biology_subjects) + (1 if biology_subjects else 0)
            equal_share = 1.0 / effective_subject_count if effective_subject_count > 0 else 0
            
            # Biology shares one equal portion
            if biology_subjects:
                for subject in biology_subjects:
                    distribution[subject.id] = equal_share / len(biology_subjects)
            
            # Other subjects get one equal portion each
            for subject in non_biology_subjects:
                distribution[subject.id] = equal_share
    
    return distribution

def optimize_topic_query(subject_id=None, limit=None):
    """
    Optimized query for topics.
    Reduces the number of database roundtrips for large datasets.
    
    Args:
        subject_id: Optional filter by subject ID
        limit: Optional limit on number of results
        
    Returns:
        List of topics
    """
    query = Topic.query
    
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    
    # Apply limit if specified
    if limit:
        query = query.limit(limit)
    
    # Get topics
    topics = query.all()
    
    return topics

def optimize_subtopic_query(topic_id=None, limit=None):
    """
    Optimized query for subtopics.
    
    Args:
        topic_id: Optional filter by topic ID
        limit: Optional limit on number of results
        
    Returns:
        List of subtopics
    """
    query = Subtopic.query
    
    if topic_id:
        query = query.filter_by(topic_id=topic_id)
    
    # Apply limit if specified
    if limit:
        query = query.limit(limit)
    
    # Get subtopics
    subtopics = query.all()
    
    return subtopics
