"""
File management core logic
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from app.dependencies import get_app_state, settings, logger


def load_file_database():
    """Load file information from uploads directory"""
    app_state = get_app_state()
    app_state.uploaded_files = {}
    
    try:
        for file_path in settings.UPLOAD_DIR.glob("*.nc"):
            try:
                stat = file_path.stat()
                file_id = file_path.stem.split('_')[0]  # Extract job_id
                
                # Check if we have metadata in active_visualizations
                metadata = None
                tileset_id = None
                processing_status = "unknown"
                
                if file_id in app_state.active_visualizations:
                    viz_info = app_state.active_visualizations[file_id]
                    metadata = viz_info.get('metadata')
                    tileset_id = viz_info.get('tileset_id')
                    processing_status = viz_info.get('status', 'unknown')
                
                app_state.uploaded_files[file_id] = {
                    "id": file_id,
                    "filename": file_path.name,
                    "original_filename": '_'.join(file_path.stem.split('_')[1:]) + '.nc',
                    "size": stat.st_size,
                    "upload_date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "status": "active",
                    "metadata": metadata,
                    "tileset_id": tileset_id,
                    "job_id": file_id,
                    "processing_status": processing_status,
                    "file_path": str(file_path)
                }
            except Exception as e:
                logger.error(f"Error loading file info for {file_path}: {e}")
                
    except Exception as e:
        logger.error(f"Error loading file database: {e}")


def get_file_info(file_id: str) -> Optional[Dict[str, Any]]:
    """Get information about a specific file"""
    app_state = get_app_state()
    
    if file_id not in app_state.uploaded_files:
        return None
    
    file_info = app_state.uploaded_files[file_id].copy()
    
    # Get additional info from active visualizations if available
    if file_id in app_state.active_visualizations:
        viz_info = app_state.active_visualizations[file_id]
        file_info['visualization_info'] = {
            'tileset_id': viz_info.get('tileset_id'),
            'mapbox_tileset': viz_info.get('mapbox_tileset'),
            'format': viz_info.get('format'),
            'wind_components': viz_info.get('wind_components'),
            'bounds': viz_info.get('bounds'),
            'center': viz_info.get('center'),
            'zoom': viz_info.get('zoom')
        }
    
    return file_info


def delete_file_and_cleanup(file_id: str) -> bool:
    """Delete a file and all associated data"""
    app_state = get_app_state()
    
    if file_id not in app_state.uploaded_files:
        return False
    
    file_info = app_state.uploaded_files[file_id]
    file_path = Path(file_info['file_path'])
    
    try:
        # Delete the physical file
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted file: {file_path}")
        
        # Remove from active visualizations
        if file_id in app_state.active_visualizations:
            del app_state.active_visualizations[file_id]
        
        # Remove from active sessions
        if file_id in app_state.active_sessions:
            del app_state.active_sessions[file_id]
        
        # Delete associated recipe files
        recipe_files = list(settings.RECIPE_DIR.glob(f"*{file_id}*.json"))
        for recipe_file in recipe_files:
            try:
                recipe_file.unlink()
                logger.info(f"Deleted recipe: {recipe_file}")
            except Exception as e:
                logger.error(f"Error deleting recipe: {e}")
        
        # Remove from uploaded files
        del app_state.uploaded_files[file_id]
        
        return True
        
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        return False


def search_files(files: List[Dict], search_term: str) -> List[Dict]:
    """Search files by filename"""
    search_lower = search_term.lower()
    return [f for f in files if search_lower in f['original_filename'].lower()]


def filter_files_by_status(files: List[Dict], status: str) -> List[Dict]:
    """Filter files by processing status"""
    return [f for f in files if f.get('processing_status') == status]


def sort_files(files: List[Dict], sort_by: str, order: str) -> List[Dict]:
    """Sort files by specified field"""
    reverse = (order == "desc")
    
    if sort_by == "filename":
        files.sort(key=lambda x: x['original_filename'], reverse=reverse)
    elif sort_by == "size":
        files.sort(key=lambda x: x['size'], reverse=reverse)
    elif sort_by == "upload_date":
        files.sort(key=lambda x: x['upload_date'], reverse=reverse)
    
    return files