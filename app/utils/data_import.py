import json
import os
from app import db
from app.models.curriculum import Subject, Topic, Subtopic
from app.models.task import TaskType

def import_curriculum_data(json_path, validate=True):
    """
    Import curriculum data from a JSON file into the database.
    
    Args:
        json_path (str): Path to the JSON file
        validate (bool): Whether to validate data before importing
        
    Returns:
        dict: Stats about imported data
    """
    # Initialize stats
    stats = {
        'subjects': 0,
        'topics': 0,
        'subtopics': 0,
        'validation_warnings': [],
        'errors': []
    }
    
    # Check if file exists
    if not os.path.exists(json_path):
        stats['errors'].append(f"File not found: {json_path}")
        return stats
    
    try:
        # Read JSON file
        with open(json_path, 'r') as f:
            # Parse JSONC by removing comments (lines starting with //)
            content = ""
            for line in f:
                if not line.strip().startswith('//'):
                    content += line
            
            data = json.loads(content)
        
        # Validate data structure if requested
        if validate:
            validation_results = validate_curriculum_data(data)
            stats['validation_warnings'] = validation_results['warnings']
            
            # If there are critical validation errors, abort import
            if validation_results['critical_errors']:
                stats['errors'].extend(validation_results['critical_errors'])
                return stats
        
        # Process each subject
        for subject_name, subject_data in data.items():
            # Create subject
            subject = Subject(
                title=subject_data.get('Title', subject_name),
                description=subject_data.get('Description', ''),
                value=subject_data.get('value', 1)
            )
            db.session.add(subject)
            db.session.flush()  # Get the ID without committing
            stats['subjects'] += 1
            
            # Process topics for the subject
            topics = subject_data.get('Topics', [])
            
            # Special handling for Psychology which has an extra nesting level
            if subject_name == "Psychology":
                for paper_topic in topics:
                    # Create paper topic (Paper 1, Paper 2, etc.)
                    paper = Topic(
                        title=paper_topic.get('Title', paper_topic.get('Name', 'Unknown Paper')),
                        name=paper_topic.get('Name', ''),
                        description=paper_topic.get('Description', ''),
                        subject_id=subject.id,
                        value=paper_topic.get('value', 2)  # Psychology papers are value 2
                    )
                    db.session.add(paper)
                    db.session.flush()
                    stats['topics'] += 1
                    
                    # Process subtopic categories (Social Influence, Memory, etc.)
                    subtopic_categories = paper_topic.get('Subtopics', [])
                    
                    for category in subtopic_categories:
                        # Create subtopic category as a Topic with parent_topic_id
                        category_topic = Topic(
                            title=category.get('Title', 'Unknown Category'),
                            description=category.get('Description', ''),
                            subject_id=subject.id,
                            parent_topic_id=paper.id,
                            value=category.get('value', 2)  # Category is value 2
                        )
                        db.session.add(category_topic)
                        db.session.flush()
                        stats['topics'] += 1
                        
                        # Process actual subtopics
                        subtopics_data = category.get('Subtopics', [])
                        
                        for subtopic_data in subtopics_data:
                            subtopic = Subtopic(
                                title=subtopic_data.get('Title', 'Unknown Subtopic'),
                                description=subtopic_data.get('Description', ''),
                                topic_id=category_topic.id,
                                value=subtopic_data.get('value', 4)
                            )
                            db.session.add(subtopic)
                            stats['subtopics'] += 1
            
            else:
                # Regular subject structure
                for topic_data in topics:
                    # Create topic
                    topic = Topic(
                        title=topic_data.get('Title', topic_data.get('Name', 'Unknown Topic')),
                        name=topic_data.get('Name', ''),
                        description=topic_data.get('Description', ''),
                        subject_id=subject.id,
                        value=topic_data.get('value', 3)
                    )
                    db.session.add(topic)
                    db.session.flush()
                    stats['topics'] += 1
                    
                    # Process subtopics
                    subtopics_data = topic_data.get('Subtopics', [])
                    
                    for subtopic_data in subtopics_data:
                        subtopic = Subtopic(
                            title=subtopic_data.get('Title', 'Unknown Subtopic'),
                            description=subtopic_data.get('Description', ''),
                            topic_id=topic.id,
                            value=subtopic_data.get('value', 4)
                        )
                        db.session.add(subtopic)
                        stats['subtopics'] += 1
        
        # Commit all changes
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        stats['errors'].append(f"Error importing data: {str(e)}")
    
    return stats

def validate_curriculum_data(data):
    """
    Validate curriculum data structure before importing.
    
    Args:
        data (dict): The curriculum data to validate
        
    Returns:
        dict: Validation results with warnings and critical errors
    """
    results = {
        'warnings': [],
        'critical_errors': []
    }
    
    # Check if data is a dictionary
    if not isinstance(data, dict):
        results['critical_errors'].append("Data must be a dictionary of subjects")
        return results
    
    # Check for empty data
    if not data:
        results['critical_errors'].append("No subjects found in data")
        return results
    
    # Validate each subject
    for subject_name, subject_data in data.items():
        # Check subject structure
        if not isinstance(subject_data, dict):
            results['critical_errors'].append(f"Subject '{subject_name}' data must be a dictionary")
            continue
            
        # Check for required fields
        if 'Topics' not in subject_data:
            results['warnings'].append(f"Subject '{subject_name}' has no topics")
            
        if not isinstance(subject_data.get('Topics', []), list):
            results['critical_errors'].append(f"Subject '{subject_name}' topics must be a list")
            continue
        
        # Validate topics
        for i, topic_data in enumerate(subject_data.get('Topics', [])):
            if not isinstance(topic_data, dict):
                results['critical_errors'].append(f"Topic {i} in subject '{subject_name}' must be a dictionary")
                continue
                
            # Check for required fields
            if 'Title' not in topic_data and 'Name' not in topic_data:
                results['warnings'].append(f"Topic {i} in subject '{subject_name}' has no title or name")
            
            # Psychology has nested subtopics
            if subject_name == "Psychology":
                if not isinstance(topic_data.get('Subtopics', []), list):
                    results['warnings'].append(f"Paper topic {i} in Psychology has no valid subtopics")
                    continue
                    
                # Validate nested categories
                for j, category in enumerate(topic_data.get('Subtopics', [])):
                    if not isinstance(category, dict):
                        results['warnings'].append(f"Category {j} in Paper {i} of Psychology must be a dictionary")
                        continue
                        
                    if 'Title' not in category:
                        results['warnings'].append(f"Category {j} in Paper {i} of Psychology has no title")
                    
                    if not isinstance(category.get('Subtopics', []), list):
                        results['warnings'].append(f"Category {j} in Paper {i} of Psychology has no valid subtopics")
                        continue
                        
                    # Validate subtopics
                    for k, subtopic in enumerate(category.get('Subtopics', [])):
                        if not isinstance(subtopic, dict):
                            results['warnings'].append(f"Subtopic {k} in Category {j} of Paper {i} in Psychology must be a dictionary")
                            continue
                            
                        if 'Title' not in subtopic:
                            results['warnings'].append(f"Subtopic {k} in Category {j} of Paper {i} in Psychology has no title")
            else:
                # Regular subjects
                if not isinstance(topic_data.get('Subtopics', []), list):
                    results['warnings'].append(f"Topic '{topic_data.get('Title', topic_data.get('Name', i))}' in subject '{subject_name}' has no valid subtopics")
                    continue
                    
                # Validate subtopics
                for j, subtopic in enumerate(topic_data.get('Subtopics', [])):
                    if not isinstance(subtopic, dict):
                        results['warnings'].append(f"Subtopic {j} in topic '{topic_data.get('Title', topic_data.get('Name', i))}' of subject '{subject_name}' must be a dictionary")
                        continue
                        
                    if 'Title' not in subtopic:
                        results['warnings'].append(f"Subtopic {j} in topic '{topic_data.get('Title', topic_data.get('Name', i))}' of subject '{subject_name}' has no title")
    
    return results

def verify_imported_data():
    """
    Verify that data was imported correctly by performing integrity checks.
    
    Returns:
        dict: Verification results
    """
    results = {
        'success': True,
        'issues': []
    }
    
    # Check if subjects were created
    subjects = Subject.query.all()
    if not subjects:
        results['success'] = False
        results['issues'].append("No subjects found in database")
        return results
    
    # Check each subject for topics
    for subject in subjects:
        if not subject.topics:
            results['issues'].append(f"Subject '{subject.title}' has no topics")
        
        # Check topics for subtopics
        for topic in subject.topics:
            if not topic.subtopics and not topic.child_topics:
                results['issues'].append(f"Topic '{topic.title}' in subject '{subject.title}' has no subtopics or child topics")
            
            # Check child topics for subtopics (Psychology)
            for child_topic in topic.child_topics:
                if not child_topic.subtopics:
                    results['issues'].append(f"Child topic '{child_topic.title}' of topic '{topic.title}' has no subtopics")
    
    # Check for orphaned topics
    orphaned_topics = Topic.query.filter(~Topic.id.in_(db.session.query(Subtopic.topic_id))).all()
    if orphaned_topics and not any(t.child_topics for t in orphaned_topics):
        for topic in orphaned_topics:
            if not topic.child_topics:
                results['issues'].append(f"Topic '{topic.title}' (ID: {topic.id}) has no subtopics or child topics")
    
    return results

def seed_default_data():
    """
    Seed default data in the database.
    
    Returns:
        dict: Stats about seeded data
    """
    stats = {
        'task_types': 0,
        'errors': []
    }
    
    try:
        # Create default task types
        default_types = [
            ('notes', 'Taking or reviewing notes on a topic'),
            ('quiz', 'Testing knowledge through questions'),
            ('practice', 'Applying knowledge through practice problems'),
            ('uplearn', 'Completing Uplearn modules')
        ]
        
        for name, description in default_types:
            if not TaskType.query.filter_by(name=name).first():
                task_type = TaskType(name=name, description=description)
                db.session.add(task_type)
                stats['task_types'] += 1
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        stats['errors'].append(f"Error seeding default data: {str(e)}")
    
    return stats

def create_blank_subject(user_id, title, topics_data):
    """
    Create a custom "Blank" subject with user-defined topics and subtopics.
    
    Args:
        user_id (int): ID of the user creating the subject
        title (str): Title for the blank subject (e.g., "Blank 1")
        topics_data (list): List of topics with optional subtopics
        
    Returns:
        Subject: The created subject or None on error
    """
    try:
        # Create subject
        subject = Subject(
            title=title,
            description=f"Custom subject created by user {user_id}",
            value=1,
            is_user_created=True,
            created_by_user_id=user_id
        )
        db.session.add(subject)
        db.session.flush()
        
        # Create topics and subtopics
        for topic_data in topics_data:
            topic_title = topic_data.get('title', 'Untitled Topic')
            topic_description = topic_data.get('description', '')
            
            topic = Topic(
                title=topic_title,
                description=topic_description,
                subject_id=subject.id,
                value=3,
                is_user_created=True,
                created_by_user_id=user_id
            )
            db.session.add(topic)
            db.session.flush()
            
            # Create subtopics if provided
            subtopics_data = topic_data.get('subtopics', [])
            
            for subtopic_data in subtopics_data:
                subtopic_title = subtopic_data.get('title', 'Untitled Subtopic')
                subtopic_description = subtopic_data.get('description', '')
                
                subtopic = Subtopic(
                    title=subtopic_title,
                    description=subtopic_description,
                    topic_id=topic.id,
                    value=4,
                    is_user_created=True,
                    created_by_user_id=user_id
                )
                db.session.add(subtopic)
        
        db.session.commit()
        return subject
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating blank subject: {str(e)}")
        return None
