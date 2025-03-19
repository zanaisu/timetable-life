from app.models.curriculum import Subject, Topic, Subtopic

def get_subject_code(subject_name):
    """
    Extract a standardized subject code from a subject name.
    
    Args:
        subject_name (str): The name of the subject
        
    Returns:
        str: A standardized subject code
    """
    # Special handling for Biology Y12/Y13
    if "Biology" in subject_name:
        if "12" in subject_name:
            return "BIO12"
        elif "13" in subject_name:
            return "BIO13"
        return "BIO"
    elif "Chemistry" in subject_name:
        return "CHEM"
    elif "Psychology" in subject_name:
        return "PSYCH"
    elif "Blank" in subject_name:
        return f"BLANK_{subject_name.replace(' ', '_')}"
    # Fallback for other subjects
    return subject_name.upper().replace(" ", "_")[:10]

def generate_topic_key(topic, subject_code=None):
    """
    Generate a unique key for a topic for confidence tracking.
    
    Args:
        topic (Topic): The topic object
        subject_code (str, optional): The subject code (if already known)
        
    Returns:
        str: A unique key for the topic
    """
    if not subject_code:
        subject = Subject.query.get(topic.subject_id)
        subject_code = subject.get_subject_code() if subject else "UNKNOWN"
    
    # Handle nested topics in Psychology
    if topic.parent_topic_id:
        parent = Topic.query.get(topic.parent_topic_id)
        if parent and parent.name:
            return f"{subject_code}_{parent.name.replace(' ', '_')}_{topic.title.replace(' ', '_')}"
    
    # Regular topics
    if topic.name:
        return f"{subject_code}_{topic.name.replace(' ', '_')}"
    else:
        return f"{subject_code}_{topic.title.replace(' ', '_')}"

def generate_subtopic_key(subtopic):
    """
    Generate a unique key for a subtopic for confidence tracking.
    
    Args:
        subtopic (Subtopic): The subtopic object
        
    Returns:
        str: A unique key for the subtopic
    """
    topic = Topic.query.get(subtopic.topic_id)
    if not topic:
        return f"UNKNOWN_{subtopic.title.replace(' ', '_')}"
    
    topic_key = generate_topic_key(topic)
    return f"{topic_key}_{subtopic.title.replace(' ', '_')}"

def get_topic_by_key(topic_key):
    """
    Retrieve a topic by its generated key.
    
    Args:
        topic_key (str): The topic key
        
    Returns:
        Topic: The topic object if found, None otherwise
    """
    # Parse the key to extract components
    parts = topic_key.split('_')
    
    if len(parts) < 2:
        return None
    
    subject_code = parts[0]
    
    # Handle special case for Biology
    if subject_code in ["BIO12", "BIO13"]:
        if subject_code == "BIO12":
            subject = Subject.query.filter(Subject.title.like("Biology Year 12%")).first()
        else:
            subject = Subject.query.filter(Subject.title.like("Biology Year 13%")).first()
    elif subject_code == "CHEM":
        subject = Subject.query.filter(Subject.title.like("Chemistry%")).first()
    elif subject_code == "PSYCH":
        subject = Subject.query.filter(Subject.title.like("Psychology%")).first()
    elif subject_code.startswith("BLANK_"):
        # Custom subject
        blank_id = subject_code.split("_")[1]
        subject = Subject.query.filter(Subject.title.like(f"Blank {blank_id}%")).first()
    else:
        # General fallback
        subject = Subject.query.filter(Subject.title.like(f"{parts[0]}%")).first()
    
    if not subject:
        return None
    
    # Try to find the topic
    if len(parts) > 2:
        # Could be a module number like "Module_1"
        module_name = parts[1].replace('_', ' ')
        topic = Topic.query.filter_by(subject_id=subject.id, name=module_name).first()
        
        if not topic:
            # Could be a topic title
            topic_title = '_'.join(parts[1:]).replace('_', ' ')
            topic = Topic.query.filter_by(subject_id=subject.id, title=topic_title).first()
    else:
        # Simple case, just a subject and topic title
        topic_title = parts[1].replace('_', ' ')
        topic = Topic.query.filter_by(subject_id=subject.id, title=topic_title).first()
    
    return topic

def get_subtopic_by_key(subtopic_key):
    """
    Retrieve a subtopic by its generated key.
    
    Args:
        subtopic_key (str): The subtopic key
        
    Returns:
        Subtopic: The subtopic object if found, None otherwise
    """
    # First, find the last underscore to separate topic_key from subtopic
    last_underscore = subtopic_key.rfind('_')
    if last_underscore == -1:
        return None
    
    topic_key = subtopic_key[:last_underscore]
    subtopic_title = subtopic_key[last_underscore + 1:].replace('_', ' ')
    
    # Find the topic
    topic = get_topic_by_key(topic_key)
    if not topic:
        return None
    
    # Find the subtopic by title within this topic
    subtopic = Subtopic.query.filter_by(topic_id=topic.id, title=subtopic_title).first()
    
    return subtopic
