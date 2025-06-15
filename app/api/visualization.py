"""
Visualization API endpoints
"""

from fastapi import APIRouter, HTTPException
from app.dependencies import get_app_state, logger
from app.models.visualization import VisualizationStatus, WindDataResponse

router = APIRouter()


@router.get("/visualization-status/{job_id}", response_model=VisualizationStatus)
async def get_visualization_status(job_id: str):
    """Get status of visualization processing"""
    app_state = get_app_state()
    
    if job_id not in app_state.active_visualizations:
        raise HTTPException(404, "Job not found")
    
    viz_info = app_state.active_visualizations[job_id]
    
    # Update file database status if needed
    if job_id in app_state.uploaded_files:
        app_state.uploaded_files[job_id]['processing_status'] = viz_info.get('status', 'processing')
        if viz_info.get('error'):
            app_state.uploaded_files[job_id]['error'] = viz_info.get('error')
    
    return VisualizationStatus(**viz_info)


@router.get("/wind-data/{session_id}", response_model=WindDataResponse)
async def get_wind_data(session_id: str):
    """Get wind data for client-side animation"""
    app_state = get_app_state()
    
    if session_id not in app_state.active_sessions:
        # Try to load from active visualizations
        if session_id in app_state.active_visualizations:
            viz_info = app_state.active_visualizations[session_id]
            file_path = viz_info.get('file_path')
            
            if file_path and os.path.exists(file_path):
                try:
                    from app.core.wind_analyzer import extract_wind_data_for_client
                    import xarray as xr
                    
                    ds = xr.open_dataset(file_path)
                    wind_components = viz_info.get('wind_components')
                    bounds = viz_info.get('bounds')
                    
                    if wind_components:
                        wind_data = extract_wind_data_for_client(ds, wind_components, bounds)
                        ds.close()
                        
                        if wind_data:
                            return WindDataResponse(success=True, **wind_data)
                except Exception as e:
                    logger.error(f"Error re-extracting wind data: {e}")
        
        raise HTTPException(404, "Session not found")
    
    session_data = app_state.active_sessions[session_id]
    wind_data = session_data.get('wind_data')
    
    if not wind_data:
        raise HTTPException(404, "No wind data available for this session")
    
    return WindDataResponse(success=True, **wind_data)


@router.get("/active-visualizations")
async def get_active_visualizations():
    """Get list of active visualizations"""
    app_state = get_app_state()
    
    # Group by batch if applicable
    batched_visualizations = {}
    single_visualizations = []
    
    for job_id, viz in app_state.active_visualizations.items():
        batch_id = viz.get('batch_id')
        viz_data = {
            "job_id": job_id,
            "tileset_id": viz.get('tileset_id'),
            "mapbox_tileset": viz.get('mapbox_tileset'),
            "status": viz.get('status', 'processing'),
            "created_at": viz.get('created_at'),
            "format": viz.get('format', 'vector'),
            "actual_format": viz.get('actual_format', viz.get('format', 'vector')),
            "requested_format": viz.get('requested_format', 'vector'),
            "wind_components": viz.get('wind_components'),
            "scalar_vars": viz.get('scalar_vars', []),
            "vector_pairs": viz.get('vector_pairs', []),
            "use_client_animation": viz.get('use_client_animation', False),
            "session_id": viz.get('session_id'),
            "bounds": viz.get('bounds'),
            "center": viz.get('center'),
            "zoom": viz.get('zoom')
        }
        
        if batch_id:
            if batch_id not in batched_visualizations:
                batched_visualizations[batch_id] = []
            batched_visualizations[batch_id].append(viz_data)
        else:
            single_visualizations.append(viz_data)
    
    return {
        "single_visualizations": single_visualizations,
        "batched_visualizations": batched_visualizations,
        "batch_jobs": app_state.batch_jobs
    }


@router.delete("/visualization/{job_id}")
async def delete_visualization(job_id: str):
    """Delete a visualization and its files"""
    app_state = get_app_state()
    
    if job_id not in app_state.active_visualizations:
        raise HTTPException(404, "Visualization not found")
    
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
    
    return {"success": True, "message": "Visualization deleted"}