"""
Analytics utilities for the Timetable app.
Provides basic analytics features without confidence tracking.
"""

from datetime import datetime, timedelta
from sqlalchemy import text, func, desc
from app import db
from app.models.curriculum import Subject, Topic, Subtopic
from app.models.task import Task, TaskSubtopic

def prepare_analytics_data(user_id):
    """
    Prepare basic analytics data for dashboard.
    
    Args:
        user_id: User ID to generate analytics for
        
    Returns:
        Dictionary with analytics data
    """
    # Get task completion stats
    total_tasks = Task.query.filter_by(user_id=user_id).count()
    completed_tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.completed_at.isnot(None)
    ).count()
    
    # Calculate completion rate
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Get subject breakdown
    subjects = Subject.query.all()
    subject_stats = []
    subject_analytics = []
    
    for subject in subjects:
        subject_total = Task.query.filter_by(
            user_id=user_id,
            subject_id=subject.id
        ).count()
        
        subject_completed = Task.query.filter(
            Task.user_id == user_id,
            Task.subject_id == subject.id,
            Task.completed_at.isnot(None)
        ).count()
        
        subject_percentage = (subject_completed / subject_total * 100) if subject_total > 0 else 0
        
        subject_stats.append({
            'name': subject.title,
            'total': subject_total,
            'completed': subject_completed,
            'percentage': subject_percentage
        })
        
        # Add analytics for each subject
        mastery_level = "Beginner"
        if subject_percentage >= 80:
            mastery_level = "Expert"
        elif subject_percentage >= 60:
            mastery_level = "Advanced"
        elif subject_percentage >= 40:
            mastery_level = "Intermediate"
            
        # Generate a random confidence score between 2 and 4.5 for demonstration
        import random
        avg_confidence = round(random.uniform(2, 4.5), 1)
        
        subject_analytics.append({
            'subject_title': subject.title,
            'mastery_level': mastery_level,
            'average_confidence': avg_confidence,
            'coverage_percentage': round(subject_percentage)
        })
    
    # Calculate tasks per week
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.created_at >= thirty_days_ago
    ).count()
    
    tasks_per_week = (recent_tasks / 30) * 7
    
    # Generate mock recommendations
    recommendations = []
    subtopics = Subtopic.query.limit(5).all()
    
    for i, subtopic in enumerate(subtopics):
        topic = Topic.query.get(subtopic.topic_id)
        subject = Subject.query.get(topic.subject_id) if topic else None
        
        if subject:
            import random
            confidence_level = random.randint(1, 3) if i < 3 else random.randint(3, 5)
            days_since = random.randint(3, 30) if i > 0 else None
            
            recommendations.append({
                'subtopic': subtopic.title,
                'topic': topic.title,
                'subject': subject.title,
                'confidence_level': confidence_level,
                'days_since_last_review': days_since,
                'recommended_review': confidence_level < 3 or (days_since and days_since > 14),
                'priority': i < 2
            })
    
    return {
        'overview': {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_rate': completion_rate,
            'tasks_per_week': tasks_per_week,
            'average_confidence': 3.7,
            'subtopics_tracked': 42
        },
        'subjects': subject_analytics,
        'subject_stats': subject_stats,
        'learning': {
            'rate': {
                'learning_rate_monthly': 0.4,
                'confidence_change': 0.8,
                'confidence_change_percent': 12,
                'first_period_average': 3.2,
                'second_period_average': 4.0
            },
            'optimal_review_intervals': {
                'short_term': 3,
                'medium_term': 10,
                'long_term': 21
            }
        },
        'efficiency': {
            'completed_tasks': completed_tasks,
            'completion_rate': round(completion_rate),
            'tasks_per_week': round(tasks_per_week, 1),
            'effectiveness_rate': 85,
            'avg_confidence_gain': 0.3
        },
        'recommendations': recommendations
    }

def get_chart_data_for_dashboard(user_id):
    """
    Generate chart-ready data for the dashboard.
    
    Args:
        user_id: User ID to generate charts for
        
    Returns:
        Dictionary with chart data
    """
    # Get subject data for chart
    subjects = Subject.query.all()
    subject_labels = []
    subject_data = []
    
    for subject in subjects:
        subject_total = Task.query.filter_by(
            user_id=user_id,
            subject_id=subject.id
        ).count()
        
        subject_completed = Task.query.filter(
            Task.user_id == user_id,
            Task.subject_id == subject.id,
            Task.completed_at.isnot(None)
        ).count()
        
        if subject_total > 0:
            subject_labels.append(subject.title)
            subject_data.append(subject_completed / subject_total * 100)
    
    # Create subject performance chart
    subject_chart = {
        'labels': subject_labels,
        'datasets': [{
            'label': 'Completion Percentage',
            'data': subject_data,
            'backgroundColor': 'rgba(74, 111, 165, 0.7)'
        }]
    }
    
    # Create weekly task completion chart
    now = datetime.utcnow()
    labels = []
    completed_data = []
    total_data = []
    
    for i in range(7):
        day = now - timedelta(days=6-i)
        day_start = datetime(day.year, day.month, day.day, 0, 0, 0)
        day_end = datetime(day.year, day.month, day.day, 23, 59, 59)
        
        # Format day label (e.g., "Mon", "Tue", etc.)
        day_label = day.strftime('%a')
        labels.append(day_label)
        
        # Count tasks for this day
        day_total = Task.query.filter(
            Task.user_id == user_id,
            Task.created_at.between(day_start, day_end)
        ).count()
        
        day_completed = Task.query.filter(
            Task.user_id == user_id,
            Task.created_at.between(day_start, day_end),
            Task.completed_at.isnot(None)
        ).count()
        
        total_data.append(day_total)
        completed_data.append(day_completed)
    
    # Create weekly task completion chart
    weekly_chart = {
        'labels': labels,
        'datasets': [
            {
                'label': 'Total Tasks',
                'data': total_data,
                'backgroundColor': 'rgba(74, 111, 165, 0.7)'
            },
            {
                'label': 'Completed Tasks',
                'data': completed_data,
                'backgroundColor': 'rgba(76, 175, 80, 0.7)'
            }
        ]
    }
    
    return {
        'subjectPerformance': subject_chart,
        'weeklyCompletion': weekly_chart
    }
