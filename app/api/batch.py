"""
Batch processing API endpoints
"""

from fastapi import APIRouter, HTTPException
from app.dependencies import get_app_state, logger

router = APIRouter()


@router.get("/batch-status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get status of batch processing"""
    app_state = get_app_state()
    
    if batch_id not in app_state.batch_jobs:
        raise HTTPException(404, "Batch job not found")
    
    batch_info = app_state.batch_jobs[batch_id]
    
    # Check individual file statuses
    completed = 0
    failed = 0
    processing = 0
    
    for file_info in batch_info['files']:
        job_id = file_info.get('job_id')
        if job_id in app_state.active_visualizations:
            status = app_state.active_visualizations[job_id].get('status', 'processing')
            if status == 'completed':
                completed += 1
            elif status == 'failed':
                failed += 1
            else:
                processing += 1
    
    # Update batch status
    if processing > 0:
        batch_info['status'] = 'processing'
    elif failed == len(batch_info['files']):
        batch_info['status'] = 'failed'
    elif completed == len(batch_info['files']):
        batch_info['status'] = 'completed'
    else:
        batch_info['status'] = 'partial'
    
    batch_info['completed_files'] = completed
    batch_info['failed_files'] = failed
    batch_info['processing_files'] = processing
    
    return batch_info


@router.delete("/batch/{batch_id}")
async def delete_batch(batch_id: str):
    """Delete all visualizations in a batch"""
    app_state = get_app_state()
    
    if batch_id not in app_state.batch_jobs:
        raise HTTPException(404, "Batch not found")
    
    batch_info = app_state.batch_jobs[batch_id]
    deleted_count = 0
    
    # Delete all visualizations in the batch
    for file_info in batch_info['files']:
        job_id = file_info.get('job_id')
        if job_id and job_id in app_state.active_visualizations:
            viz_info = app_state.active_visualizations[job_id]
            
            # Delete uploaded file
            try:
                file_path = Path(viz_info['file_path'])
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted file: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
            
            # Remove from active visualizations
            del app_state.active_visualizations[job_id]
            
            # Remove from active sessions if exists
            if job_id in app_state.active_sessions:
                del app_state.active_sessions[job_id]
            
            # Remove from uploaded files
            if job_id in app_state.uploaded_files:
                del app_state.uploaded_files[job_id]
            
            deleted_count += 1
    
    # Remove batch job
    del app_state.batch_jobs[batch_id]
    
    return {
        "success": True,
        "message": f"Batch deleted. Removed {deleted_count} visualizations.",
        "deleted_count": deleted_count
    }