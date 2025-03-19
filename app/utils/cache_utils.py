from functools import wraps
from flask import make_response, request, current_app
from app import cache
import hashlib
import re

def cache_response(timeout=None, key_prefix='view'):
    """
    Cache response decorator that works with both API and HTML responses.
    Uses the request path and query parameters to build the cache key.
    
    Args:
        timeout: Cache timeout in seconds (defaults to app config)
        key_prefix: Prefix for the cache key
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip caching for POST/PUT/DELETE requests
            if request.method != 'GET':
                return f(*args, **kwargs)
            
            # Skip caching for logged-in users if needed
            # from flask_login import current_user
            # if current_user.is_authenticated:
            #     return f(*args, **kwargs)
            
            # Create a cache key based on the full request path and args
            cache_key = key_prefix + ':' + request.full_path
            
            # Try to get the response from the cache
            response = cache.get(cache_key)
            
            # If not in cache, call the original function and cache the response
            if response is None:
                response = f(*args, **kwargs)
                timeout_value = timeout or current_app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
                cache.set(cache_key, response, timeout=timeout_value)
            
            return response
        return decorated_function
    return decorator

def add_cache_headers(response, max_age=None, etag=None):
    """
    Add cache control headers to a Flask response.
    
    Args:
        response: Flask response object
        max_age: Cache max-age in seconds (defaults to app config)
        etag: Custom ETag value (if None, generate from response data)
    
    Returns:
        Modified response with cache headers
    """
    # Convert response to a response object if it's not already
    if not isinstance(response, tuple) and not hasattr(response, 'headers'):
        response = make_response(response)
    elif isinstance(response, tuple):
        response = make_response(response)
    
    # Set Cache-Control header
    if max_age is None:
        max_age = current_app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
    
    # Set appropriate cache headers
    response.headers['Cache-Control'] = f'public, max-age={max_age}'
    
    # Add ETag if response has data
    if etag is None and hasattr(response, 'data') and response.data:
        etag = hashlib.md5(response.data).hexdigest()
    
    if etag:
        response.headers['ETag'] = f'"{etag}"'
    
    return response

def cache_static_files(app, max_age=86400):  # Default 1 day
    """
    Configure the Flask app to cache static files.
    
    Args:
        app: Flask app instance
        max_age: Cache max-age in seconds for static files
    """
    @app.after_request
    def add_cache_headers_to_static(response):
        # Check if the request is for a static file
        if request.path.startswith('/static/'):
            # Set cache headers for different types of static files
            if re.search(r'\.(css|js|jpg|jpeg|png|gif|ico|woff2|woff|ttf|svg)$', request.path):
                response.headers['Cache-Control'] = f'public, max-age={max_age}'
                
                # Add far-future expiration for immutable content with hash in filename
                if re.search(r'\.[0-9a-f]{8,}\.(css|js|jpg|jpeg|png|gif|svg)$', request.path):
                    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        
        return response
    
    return app 