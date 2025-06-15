"""
File management API endpoints
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from app.dependencies import get_app_state, logger
from app.models.file import FileInfo, FileListResponse, FileDeleteResponse, BatchDeleteResponse
from app.core.file_manager import (
    load_file_database,
    get_file_info,
    delete_file_and_cleanup,
    search_files,
    filter_files_by_status,
    sort_files
)

router = APIRouter()


@router.get("/files", response_model=FileListResponse)
async def list_files(
    search: Optional[str] = Query(None, description="Search term for filename"),
    status: Optional[str] = Query(None, description="Filter by status"),
    sort_by: Optional[str] = Query("upload_date", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc/desc)")
):
    """List all uploaded NetCDF files with optional filtering and sorting"""
    # Reload file database to get latest info
    load_file_database()
    
    app_state = get_app_state()
    files = list(app_state.uploaded_files.values())
    
    # Apply search filter
    if search:
        files = search_files(files, search)
    
    # Apply status filter
    if status and status != "all":
        files = filter_files_by_status(files, status)
    
    # Sort files
    files = sort_files(files, sort_by, sort_order)
    
    return FileListResponse(
        success=True,
        files=files,
        total=len(files)
    )


@router.get("/file/{file_id}", response_model=FileInfo)
async def get_file_details(file_id: str):
    """Get detailed information about a specific file"""
    file_info = get_file_info(file_id)
    
    if not file_info:
        raise HTTPException(404, "File not found")
    
    return file_info


@router.delete("/file/{file_id}", response_model=FileDeleteResponse)
async def delete_file(file_id: str):
    """Delete an uploaded file and its associated data"""
    app_state = get_app_state()
    
    if file_id not in app_state.uploaded_files:
        raise HTTPException(404, "File not found")
    
    try:
        success = delete_file_and_cleanup(file_id)
        
        if success:
            return FileDeleteResponse(
                success=True,
                message="File deleted successfully",
                file_id=file_id
            )
        else:
            raise HTTPException(500, "Failed to delete file")
            
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(500, f"Failed to delete file: {str(e)}")


@router.post("/files/delete-batch", response_model=BatchDeleteResponse)
async def delete_files_batch(file_ids: List[str]):
    """Delete multiple files at once"""
    deleted = []
    errors = []
    
    for file_id in file_ids:
        try:
            if delete_file_and_cleanup(file_id):
                deleted.append(file_id)
            else:
                errors.append({"file_id": file_id, "error": "File not found"})
        except Exception as e:
            errors.append({"file_id": file_id, "error": str(e)})
    
    return BatchDeleteResponse(
        success=len(deleted) > 0,
        deleted=deleted,
        errors=errors,
        message=f"Deleted {len(deleted)} files, {len(errors)} errors"
    )


@router.get("/file/{file_id}/download")
async def download_file(file_id: str):
    """Download the original NetCDF file"""
    from fastapi.responses import FileResponse
    
    app_state = get_app_state()
    
    if file_id not in app_state.uploaded_files:
        raise HTTPException(404, "File not found")
    
    file_info = app_state.uploaded_files[file_id]
    file_path = file_info.get('file_path')
    
    if not file_path or not Path(file_path).exists():
        raise HTTPException(404, "File no longer exists on disk")
    
    return FileResponse(
        path=file_path,
        filename=file_info['original_filename'],
        media_type='application/x-netcdf'
    )


@router.post("/file/{file_id}/reprocess")
async def reprocess_file(
    background_tasks: BackgroundTasks,
    file_id: str,
    visualization_type: str = "vector"
):
    """Reprocess an existing NetCDF file"""
    from app.services.processing import process_netcdf_file
    from app.services.background import create_mapbox_tileset_background
    
    app_state = get_app_state()
    
    if file_id not in app_state.uploaded_files:
        raise HTTPException(404, "File not found")
    
    file_info = app_state.uploaded_files[file_id]
    file_path = Path(file_info['file_path'])
    
    if not file_path.exists():
        raise HTTPException(404, "File no longer exists on disk")
    
    try:
        # Process file again
        result = await process_netcdf_file(
            file_path, file_id, True, None, visualization_type
        )
        
        if result.get('wind_data'):
            app_state.active_sessions[file_id] = {
                'file_path': str(file_path),
                'wind_data': result['wind_data'],
                'bounds': result.get('bounds'),
                'center': result.get('center'),
                'zoom': result.get('zoom'),
                'created_at': datetime.now().isoformat()
            }
            result['session_id'] = file_id
        
        if settings.MAPBOX_TOKEN and settings.MAPBOX_USERNAME:
            # Start background tileset creation
            background_tasks.add_task(
                create_mapbox_tileset_background,
                file_path,
                file_id,
                result.get('tileset_id'),
                visualization_type
            )
            
            result['status'] = 'processing'
            result['message'] = f'Reprocessing file {file_info["original_filename"]}...'
        
        # Update file info
        app_state.uploaded_files[file_id]['processing_status'] = 'processing'
        app_state.uploaded_files[file_id]['metadata'] = result.get('metadata')
        
        return result
        
    except Exception as e:
        logger.error(f"Error reprocessing file {file_id}: {e}")
        raise HTTPException(500, f"Failed to reprocess file: {str(e)}")