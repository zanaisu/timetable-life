"""
Optimization utilities for handling large datasets efficiently.
Provides caching, batch processing, and query optimization for the Timetable app.
"""

# Import from modular files
from app.utils.optimization_cache import cached, clear_cache, clear_cache_for_function
from app.utils.optimization_batch import batch_process
from app.utils.optimization_queries import (
    get_optimized_subject_distribution, 
    optimize_topic_query,
    optimize_subtopic_query
)
from app.utils.optimization_tasks import generate_tasks_in_batch

# Re-export all functions to maintain backward compatibility
__all__ = [
    'cached',
    'clear_cache',
    'clear_cache_for_function',
    'get_optimized_subject_distribution',
    'batch_process',
    'optimize_topic_query',
    'optimize_subtopic_query',
    'generate_tasks_in_batch'
]
