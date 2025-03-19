import json
import os
from app import db
from app.models.curriculum import Subject, Topic, Subtopic
from sqlalchemy.exc import SQLAlchemyError

def import_curriculum_data():
    """Import curriculum data from JSONC file to the database."""
    try:
        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                'data', 'curriculum.jsonc')
        
        # Read the JSONC file and strip comments
        with open(data_path, 'r') as f:
            content = f.read()
            # Remove single-line comments
            lines = [line for line in content.split('\n') if not line.strip().startswith('//')]
            clean_content = '\n'.join(lines)
        
        # Parse the JSON
        curriculum_data = json.loads(clean_content)
        
        # Import the data within a transaction
        for subject_name, subject_data in curriculum_data.items():
            subject_title = subject_data.get('Title', subject_name)
            
            # Improved duplicate checking - match by title or by course code
            existing_subject = None
            
            # Check for exact title match
            existing_subject = Subject.query.filter_by(title=subject_title).first()
            
            # If not found by exact title, try to match by course code
            if not existing_subject and '(' in subject_title and ')' in subject_title:
                # Extract course code like H420, H432, etc.
                course_code = subject_title.split('(')[-1].split(')')[0]
                if course_code:
                    # Find any subject with the same course code
                    for subject in Subject.query.all():
                        if course_code in subject.title:
                            existing_subject = subject
                            break
            
            if existing_subject:
                print(f"Skipping duplicate subject: {subject_title}")
                continue
                
            # Create the subject
            subject = Subject(
                title=subject_data.get('Title', subject_name),
                description=subject_data.get('Description', ''),
                value=subject_data.get('value', 1)
            )
            db.session.add(subject)
            db.session.flush()  # To get the ID
            
            # Create the topics
            if 'Topics' in subject_data:
                for topic_data in subject_data['Topics']:
                    # Check if Psychology has special structure (we'll handle both cases)
                    if subject_name == "Psychology" and isinstance(topic_data.get('Subtopics', []), list) and \
                       any(isinstance(st, dict) and 'Subtopics' in st for st in topic_data.get('Subtopics', [])):
                        # Psychology has a nested structure
                        # Create main topic (e.g., "Paper 1")
                        paper_topic = Topic(
                            subject_id=subject.id,
                            name=topic_data.get('Name', ''),
                            title=topic_data.get('Title', ''),
                            description=topic_data.get('Description', ''),
                            value=topic_data.get('value', 3)
                        )
                        db.session.add(paper_topic)
                        db.session.flush()
                        
                        # For each category (e.g., "Social Influence") create a child topic
                        for category in topic_data.get('Subtopics', []):
                            category_topic = Topic(
                                subject_id=subject.id,
                                parent_topic_id=paper_topic.id,
                                name=category.get('Name', ''),
                                title=category.get('Title', ''),
                                description=category.get('Description', ''),
                                value=category.get('value', 3)
                            )
                            db.session.add(category_topic)
                            db.session.flush()
                            
                            # Create subtopics for this category
                            for subtopic_data in category.get('Subtopics', []):
                                subtopic = Subtopic(
                                    topic_id=category_topic.id,
                                    title=subtopic_data.get('Title', ''),
                                    description=subtopic_data.get('Description', ''),
                                    value=subtopic_data.get('value', 4),
                                    estimated_duration=15  # Default duration
                                )
                                db.session.add(subtopic)
                    else:
                        # Standard topic structure
                        topic = Topic(
                            subject_id=subject.id,
                            name=topic_data.get('Name', ''),
                            title=topic_data.get('Title', ''),
                            description=topic_data.get('Description', ''),
                            value=topic_data.get('value', 3)
                        )
                        db.session.add(topic)
                        db.session.flush()  # To get the ID
                        
                        # Create the subtopics
                        if 'Subtopics' in topic_data:
                            for subtopic_data in topic_data['Subtopics']:
                                subtopic = Subtopic(
                                    topic_id=topic.id,
                                    title=subtopic_data.get('Title', ''),
                                    description=subtopic_data.get('Description', ''),
                                    value=subtopic_data.get('value', 4),
                                    estimated_duration=15  # Default duration
                                )
                                db.session.add(subtopic)
        
        # Commit the transaction
        db.session.commit()
        return True, "Curriculum data imported successfully."
        
    except FileNotFoundError:
        return False, "Curriculum data file not found."
    except json.JSONDecodeError:
        return False, "Error parsing curriculum data file."
    except SQLAlchemyError as e:
        db.session.rollback()
        return False, f"Database error: {str(e)}"
    except Exception as e:
        db.session.rollback()
        return False, f"Unexpected error: {str(e)}"
