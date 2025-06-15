"""
Dataset-related API endpoints
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from app.dependencies import settings, logger, get_app_state
from app.core.mapbox_client import MapboxClient
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/upload-netcdf-as-dataset")
async def upload_netcdf_as_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    dataset_name: Optional[str] = Form(None)
):
    """Upload NetCDF file and create a Mapbox dataset"""
    
    # Validate file
    if not file.filename.endswith('.nc'):
        raise HTTPException(400, "Only NetCDF (.nc) files are allowed")
    
    # Check file size
    content = await file.read()
    file_size = len(content)
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Maximum size is {settings.MAX_FILE_SIZE / 1024 / 1024}MB")
    
    # Create job
    job_id = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Save file temporarily
    safe_filename = Path(file.filename).name
    safe_filename = ''.join(c if c.isalnum() or c in '.-_' else '_' for c in safe_filename)
    file_path = settings.UPLOAD_DIR / f"{job_id}_{safe_filename}"
    
    try:
        import aiofiles
        async with aiofiles.open(str(file_path), 'wb') as f:
            await f.write(content)
        
        # Process in background
        from app.services.dataset_service import create_dataset_background
        background_tasks.add_task(
            create_dataset_background,
            file_path,
            job_id,
            dataset_name,
            file.filename
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "message": "File uploaded. Creating dataset...",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error uploading file for dataset: {str(e)}")
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(500, str(e))


@router.get("/dataset-status/{job_id}")
async def get_dataset_status(job_id: str):
    """Get status of dataset creation"""
    app_state = get_app_state()
    
    if job_id not in app_state.active_datasets:
        raise HTTPException(404, "Job not found")
    
    return app_state.active_datasets[job_id]


@router.get("/list-datasets")
async def list_datasets():
    """List all user's datasets"""
    if not settings.MAPBOX_TOKEN:
        raise HTTPException(500, "Mapbox token not configured")
    
    try:
        client = MapboxClient()
        datasets = client.list_datasets(limit=100)
        
        # Filter weather-related datasets
        weather_datasets = []
        for ds in datasets:
            dataset_name = ds.get('name', '').lower()
            dataset_id = ds.get('id', '')
            
            if any(keyword in dataset_name or keyword in dataset_id.lower() 
                  for keyword in ['weather', 'netcdf', 'wind', 'temperature', 'pressure']):
                weather_datasets.append(ds)
        
        return {
            "success": True,
            "total_datasets": len(datasets),
            "weather_datasets": weather_datasets,
            "all_datasets": datasets
        }
        
    except Exception as e:
        logger.error(f"Error listing datasets: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/dataset-info/{dataset_id}")
async def get_dataset_info(dataset_id: str):
    """Get detailed information about a dataset"""
    if not settings.MAPBOX_TOKEN:
        raise HTTPException(500, "Mapbox token not configured")
    
    try:
        client = MapboxClient()
        info = client.dataset_manager.get_dataset_info(dataset_id)
        
        if 'error' in info:
            raise HTTPException(404, info['error'])
        
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset info: {str(e)}")
        raise HTTPException(500, str(e))


@router.delete("/dataset/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Delete a dataset"""
    if not settings.MAPBOX_TOKEN:
        raise HTTPException(500, "Mapbox token not configured")
    
    try:
        client = MapboxClient()
        success = client.delete_dataset(dataset_id)
        
        if success:
            # Remove from active datasets if exists
            app_state = get_app_state()
            for job_id, ds_info in list(app_state.active_datasets.items()):
                if ds_info.get('dataset_id') == dataset_id:
                    del app_state.active_datasets[job_id]
            
            return {"success": True, "message": "Dataset deleted successfully"}
        else:
            raise HTTPException(400, "Failed to delete dataset")
            
    except Exception as e:
        logger.error(f"Error deleting dataset: {str(e)}")
        raise HTTPException(500, str(e))