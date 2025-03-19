"""
Caching utilities for handling large datasets efficiently.
Provides caching mechanisms to improve performance for the Timetable app.
"""

import time
import functools

# Cache storage
_cache = {}
_cache_timeout = {}

def cached(timeout_seconds=300):
    """
    Decorator for caching function results.
    
    Args:
        timeout_seconds: Number of seconds to keep results in cache
        
    Returns:
        Decorated function with caching capability
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check if result is in cache and not expired
            current_time = time.time()
            if key in _cache and _cache_timeout.get(key, 0) > current_time:
                return _cache[key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache[key] = result
            _cache_timeout[key] = current_time + timeout_seconds
            
            return result
        return wrapper
    return decorator

def clear_cache():
    """Clear all cached data."""
    global _cache, _cache_timeout
    _cache = {}
    _cache_timeout = {}

def clear_cache_for_function(func_name):
    """
    Clear cache entries for a specific function.
    
    Args:
        func_name: Name of the function to clear cache for
    """
    keys_to_remove = [k for k in _cache if k.startswith(f"{func_name}:")]
    for key in keys_to_remove:
        _cache.pop(key, None)
        _cache_timeout.pop(key, None)
