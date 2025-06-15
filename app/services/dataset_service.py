"""
Dataset service for background processing
"""

from pathlib import Path
from typing import Optional
from datetime import datetime
from app.dependencies import settings, logger, get_app_state
from app.core.mapbox_client import MapboxClient


async def create_dataset_background(
    file_path: Path,
    job_id: str,
    dataset_name: Optional[str],
    original_filename: str,
    batch_id: Optional[str] = None
):
    """Background task to create Mapbox dataset from NetCDF"""
    app_state = get_app_state()
    
    try:
        if not settings.MAPBOX_TOKEN:
            raise Exception("Mapbox token not configured")
        
        # Initialize dataset manager
        client = MapboxClient()
        
        # Create dataset from NetCDF
        logger.info(f"Creating dataset from {file_path}")
        
        if not dataset_name:
            dataset_name = f"Weather Data - {Path(original_filename).stem}"
        
        result = client.dataset_manager.process_netcdf_to_dataset(str(file_path), dataset_name)
        
        # Store dataset info
        if result['success']:
            app_state.active_datasets[job_id] = {
                "job_id": job_id,
                "dataset_id": result['dataset_id'],
                "dataset_url": result.get('dataset_url'),
                "filename": original_filename,
                "total_features": result.get('total_features', 0),
                "features_added": result.get('features_added', 0),
                "status": "completed",
                "created_at": datetime.now().isoformat(),
                "batch_id": batch_id
            }
            
            # Update batch job if part of batch
            if batch_id and batch_id in app_state.batch_jobs:
                app_state.batch_jobs[batch_id]['datasets'].append({
                    "dataset_id": result['dataset_id'],
                    "dataset_url": result.get('dataset_url'),
                    "filename": original_filename,
                    "features": result.get('features_added', 0)
                })
                
                # Update file status
                for file_info in app_state.batch_jobs[batch_id]['files']:
                    if file_info.get('job_id') == job_id:
                        file_info['status'] = 'completed'
                        file_info['dataset_id'] = result['dataset_id']
                        break
                
                app_state.batch_jobs[batch_id]['processed_files'] += 1
                
                # Update batch status
                if app_state.batch_jobs[batch_id]['processed_files'] == app_state.batch_jobs[batch_id]['total_files']:
                    app_state.batch_jobs[batch_id]['status'] = 'completed'
                elif app_state.batch_jobs[batch_id]['processed_files'] > 0:
                    app_state.batch_jobs[batch_id]['status'] = 'partial'
            
            logger.info(f"Successfully created dataset: {result['dataset_id']}")
            
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Failed to create dataset: {error_msg}")
            
            app_state.active_datasets[job_id] = {
                "job_id": job_id,
                "filename": original_filename,
                "status": "failed",
                "error": error_msg,
                "created_at": datetime.now().isoformat(),
                "batch_id": batch_id
            }
            
            # Update batch job if part of batch
            if batch_id and batch_id in app_state.batch_jobs:
                for file_info in app_state.batch_jobs[batch_id]['files']:
                    if file_info.get('job_id') == job_id:
                        file_info['status'] = 'failed'
                        file_info['error'] = error_msg
                        break
                
                app_state.batch_jobs[batch_id]['processed_files'] += 1
                
                if app_state.batch_jobs[batch_id]['processed_files'] == app_state.batch_jobs[batch_id]['total_files']:
                    if all(f.get('status') == 'failed' for f in app_state.batch_jobs[batch_id]['files']):
                        app_state.batch_jobs[batch_id]['status'] = 'failed'
                    else:
                        app_state.batch_jobs[batch_id]['status'] = 'partial'
        
    except Exception as e:
        logger.error(f"Error creating dataset: {str(e)}")
        import traceback
        traceback.print_exc()
        
        app_state.active_datasets[job_id] = {
            "job_id": job_id,
            "filename": original_filename,
            "status": "failed",
            "error": str(e),
            "created_at": datetime.now().isoformat(),
            "batch_id": batch_id
        }
        
        # Update batch job if part of batch
        if batch_id and batch_id in app_state.batch_jobs:
            for file_info in app_state.batch_jobs[batch_id]['files']:
                if file_info.get('job_id') == job_id:
                    file_info['status'] = 'failed'
                    file_info['error'] = str(e)
                    break
            
            app_state.batch_jobs[batch_id]['processed_files'] += 1
    
    finally:
        # Clean up file
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up file: {e}")