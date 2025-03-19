"""
Batch processing utilities for handling large datasets efficiently.
Provides functions for processing items in batches to avoid memory issues.
"""
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from app import db
import time

def batch_process(items, batch_size=100, process_func=None):
    """
    Process items in batches to avoid memory issues with large datasets.
    
    Args:
        items: List of items to process
        batch_size: Number of items to process in each batch
        process_func: Function to apply to each batch of items
        
    Returns:
        List of processed results or None if process_func is None
    """
    if not items:
        return []
    
    results = []
    
    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        if process_func:
            batch_results = process_func(batch)
            if batch_results:
                results.extend(batch_results)
        
    return results

def db_batch_process(query, batch_size=100, process_func=None, commit_per_batch=True, max_retries=3):
    """
    Process database query results in batches with proper transaction handling.
    
    Args:
        query: SQLAlchemy query object to iterate over
        batch_size: Number of items to process in each batch
        process_func: Function to apply to each batch of items
        commit_per_batch: Whether to commit after each batch
        max_retries: Maximum number of retry attempts for failed batches
        
    Returns:
        List of processed results or None if process_func is None
    """
    results = []
    offset = 0
    retry_count = 0
    
    while True:
        # Get a batch of records
        batch = query.limit(batch_size).offset(offset).all()
        
        # Break if no more records
        if not batch:
            break
            
        try:
            # Process the batch
            if process_func:
                batch_results = process_func(batch)
                if batch_results:
                    if isinstance(batch_results, list):
                        results.extend(batch_results)
                    else:
                        results.append(batch_results)
            
            # Commit if requested
            if commit_per_batch:
                db.session.commit()
                
            # Reset retry counter and advance to next batch
            retry_count = 0
            offset += len(batch)
            
        except SQLAlchemyError as e:
            # Rollback on error
            db.session.rollback()
            
            # Log the error
            current_app.logger.error(f"Batch processing error: {str(e)}")
            
            # Retry logic
            if retry_count < max_retries:
                retry_count += 1
                current_app.logger.info(f"Retrying batch (attempt {retry_count}/{max_retries})...")
                time.sleep(1)  # Wait before retry
            else:
                current_app.logger.error(f"Max retries reached for batch at offset {offset}")
                offset += len(batch)  # Skip problematic batch
                retry_count = 0
    
    return results

def db_batch_update(model, ids, update_func, batch_size=100, max_retries=3):
    """
    Update database records in batches.
    
    Args:
        model: SQLAlchemy model class
        ids: List of record IDs to update
        update_func: Function that takes a record and updates it
        batch_size: Number of records to update in each batch
        max_retries: Maximum number of retry attempts for failed batches
        
    Returns:
        Number of records successfully updated
    """
    if not ids:
        return 0
        
    updated_count = 0
    
    # Process in batches
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i + batch_size]
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Get records for this batch
                records = model.query.filter(model.id.in_(batch_ids)).all()
                
                # Apply update function to each record
                for record in records:
                    update_func(record)
                
                # Commit changes
                db.session.commit()
                updated_count += len(records)
                break  # Break retry loop on success
                
            except SQLAlchemyError as e:
                # Rollback on error
                db.session.rollback()
                
                # Log the error
                current_app.logger.error(f"Batch update error: {str(e)}")
                
                # Retry logic
                if retry_count < max_retries:
                    retry_count += 1
                    current_app.logger.info(f"Retrying batch update (attempt {retry_count}/{max_retries})...")
                    time.sleep(1)  # Wait before retry
                else:
                    current_app.logger.error(f"Max retries reached for batch update")
                    break
    
    return updated_count

def apply_to_batches(items, apply_func, batch_size=100, collector_func=None):
    """
    Apply a function to items in batches and optionally collect results.
    
    Args:
        items: List of items to process
        apply_func: Function to apply to each batch of items
        batch_size: Number of items to process in each batch
        collector_func: Optional function to collect and process results
        
    Returns:
        Collected results (if collector_func provided) or list of batch results
    """
    if not items:
        return []
    
    all_results = []
    
    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_result = apply_func(batch)
        
        if batch_result is not None:
            all_results.append(batch_result)
    
    # Apply collector function if provided
    if collector_func and all_results:
        return collector_func(all_results)
    
    return all_results
