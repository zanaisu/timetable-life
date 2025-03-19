"""
Subject selection utilities for task generation.
Handles subject distribution calculations and subject selection logic.
"""

import random
from datetime import datetime, timedelta
from sqlalchemy import text
from app import db
from app.models.curriculum import Subject, Topic

def get_subject_distribution_for_week(user):
    """
    Calculate a balanced subject distribution for the week.
    Handles special cases like Biology Y12/Y13 being counted together.
    
    Returns a dictionary with subject_id: percentage pairs.
    Enforces fixed distribution (33.33% each for Biology total, Psychology, Chemistry)
    """
    # Get all subjects
    subjects = Subject.query.all()
    
    # If no subjects exist, return an empty dictionary
    if not subjects:
        return {}
        
    # Create fixed distribution based on requirements (33.33% for each category)
    distribution = {}
    
    # Group subjects by category (Biology, Psychology, Chemistry)
    biology_subjects = [s for s in subjects if "Biology" in s.title]
    psychology_subjects = [s for s in subjects if "Psychology" in s.title]
    chemistry_subjects = [s for s in subjects if "Chemistry" in s.title]
    
    # Calculate total topic counts for Biology to split allocation proportionally
    if biology_subjects:
        bio_y12_topics = len(Topic.query.filter_by(subject_id=biology_subjects[0].id).all()) if len(biology_subjects) > 0 else 0
        bio_y13_topics = len(Topic.query.filter_by(subject_id=biology_subjects[1].id).all()) if len(biology_subjects) > 1 else 0
        
        total_bio_topics = bio_y12_topics + bio_y13_topics
        
        # Assign Biology subjects a total of 1/3 (0.3333...) share
        if total_bio_topics > 0:
            for subject in biology_subjects:
                topic_count = len(Topic.query.filter_by(subject_id=subject.id).all())
                # Divide Biology's 33.33% share based on topic proportions
                distribution[subject.id] = (1/3) * (topic_count / total_bio_topics) if total_bio_topics > 0 else 0
        else:
            # Equal split if no topic data
            for subject in biology_subjects:
                distribution[subject.id] = (1/3) / len(biology_subjects)
    
    # Assign Psychology subjects a total of 1/3 (0.3333...) share
    if psychology_subjects:
        for subject in psychology_subjects:
            distribution[subject.id] = 1/3
    
    # Assign Chemistry subjects a total of 1/3 (0.3333...) share
    if chemistry_subjects:
        for subject in chemistry_subjects:
            distribution[subject.id] = 1/3
            
    # In case any subjects are missing (data integrity check)
    for subject in subjects:
        if subject.id not in distribution:
            # If a subject doesn't fit into the main categories, assign a small share
            distribution[subject.id] = 0.01
            
    # Normalize to ensure sum is exactly 1.0
    total = sum(distribution.values())
    if total > 0:
        for subject_id in distribution:
            distribution[subject_id] /= total
    
    return distribution

def select_subject_based_on_distribution(subjects, distribution):
    """
    Select a subject based on the distribution weights.
    Treats Biology Y12 and Y13 as a single subject for selection purposes,
    ensuring Biology doesn't appear twice as often as other subjects.
    
    Args:
        subjects: List of Subject objects
        distribution: Dictionary with subject_id: weight pairs
        
    Returns:
        Selected Subject object or None if no subjects
    """
    if not subjects:
        return None
    
    # Separate Biology subjects from others
    biology_subjects = [s for s in subjects if "Biology" in s.title]
    non_biology_subjects = [s for s in subjects if "Biology" not in s.title]
    
    # If no Biology subjects, use standard selection
    if not biology_subjects:
        # Create weighted list for selection
        subject_weights = [(subject, distribution.get(subject.id, 0)) for subject in subjects]
        
        # Filter out zero-weight subjects
        subject_weights = [(subject, weight) for subject, weight in subject_weights if weight > 0]
        
        if not subject_weights:
            # Fallback to equal weighting if all weights are zero
            subject_weights = [(subject, 1) for subject in subjects]
    else:
        # Step 1: Create category weights
        # Combined weight for all Biology subjects
        biology_total_weight = sum(distribution.get(s.id, 0) for s in biology_subjects)
        
        # Weights for individual non-Biology subjects
        non_bio_weights = [(subject, distribution.get(subject.id, 0)) for subject in non_biology_subjects]
        
        # Step 2: Create category selection list
        # Biology is treated as a single category
        category_weights = [("biology", biology_total_weight)] + [(s, w) for s, w in non_bio_weights]
        
        # Filter out zero-weight categories
        category_weights = [(cat, weight) for cat, weight in category_weights if weight > 0]
        
        if not category_weights:
            # Fallback to equal weighting
            effective_count = 1 + len(non_biology_subjects)  # Biology counts as ONE
            equal_weight = 1.0 / effective_count if effective_count > 0 else 0
            
            category_weights = [("biology", equal_weight)]
            category_weights.extend([(s, equal_weight) for s in non_biology_subjects])
        
        # Step 3: Select category
        total_weight = sum(weight for _, weight in category_weights)
        
        if total_weight == 0:
            # Fallback to random with equal probability between Biology and each other subject
            choices = ["biology"] + non_biology_subjects
            category_choice = random.choice(choices)
        else:
            # Weighted selection for category
            r = random.uniform(0, total_weight)
            current_weight = 0
            
            category_choice = None
            for category, weight in category_weights:
                current_weight += weight
                if r <= current_weight:
                    category_choice = category
                    break
            
            # Fallback if no category selected
            if category_choice is None:
                category_choice = category_weights[0][0] if category_weights else "biology"
        
        # Step 4: If Biology selected, choose between Y12 and Y13 based on relative weights
        if category_choice == "biology":
            # Calculate relative weights within Biology
            if len(biology_subjects) > 1:
                # Multiple Biology subjects - weight by distribution
                bio_weights = [(s, distribution.get(s.id, 0)) for s in biology_subjects]
                bio_total = sum(w for _, w in bio_weights)
                
                if bio_total == 0:
                    # Equal weights if all zero
                    bio_weights = [(s, 1) for s in biology_subjects]
                    bio_total = len(biology_subjects)
                
                # Select Biology subject based on relative weights
                r = random.uniform(0, bio_total)
                current_weight = 0
                
                for subject, weight in bio_weights:
                    current_weight += weight
                    if r <= current_weight:
                        return subject
                
                # Fallback
                return biology_subjects[0]
            else:
                # Only one Biology subject
                return biology_subjects[0]
        else:
            # Non-Biology subject was selected
            return category_choice
    
    # Standard weighted selection for non-categorized approach
    total_weight = sum(weight for _, weight in subject_weights)
    
    if total_weight == 0:
        # Fallback to random selection
        return random.choice(subjects)
    
    # Weighted random selection
    r = random.uniform(0, total_weight)
    current_weight = 0
    
    for subject, weight in subject_weights:
        current_weight += weight
        if r <= current_weight:
            return subject
    
    # Fallback (should not be reached)
    return subjects[0] if subjects else None
