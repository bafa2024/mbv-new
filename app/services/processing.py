"""
File processing service
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import aiofiles
from app.dependencies import settings, logger, get_app_state
from app.core.netcdf_processor import process_netcdf_file


async def process_batch_upload(
    files: List[Dict],
    job_ids: List[str],
    create_tileset: bool,
    tileset_names: Optional[List[str]],
    visualization_type: str,
    background_tasks,
    batch_id: Optional[str] = None
) -> Dict[str, Any]:
    """Process multiple NetCDF files"""
    
    results = {
        "batch_id": batch_id,
        "total_files": len(files),
        "processed_files": 0,
        "status": "processing",
        "files": [],
        "errors": []
    }
    
    # Process each file
    for i, file_data in enumerate(files):
        file = file_data['file']
        content = file_data['content']
        job_id = job_ids[i]
        tileset_name = tileset_names[i] if tileset_names and i < len(tileset_names) else None
        
        try:
            # Sanitize filename
            safe_filename = Path(file.filename).name
            safe_filename = ''.join(c if c.isalnum() or c in '.-_' else '_' for c in safe_filename)
            if not safe_filename.endswith('.nc'):
                safe_filename = safe_filename.rsplit('.', 1)[0] + '.nc'
            
            # Save uploaded file
            file_path = settings.UPLOAD_DIR / f"{job_id}_{safe_filename}"
            
            logger.info(f"Saving uploaded file: {file_path}")
            
            async with aiofiles.open(str(file_path), 'wb') as f:
                await f.write(content)
            
            # Process file
            result = await process_netcdf_file(
                file_path, job_id, create_tileset, tileset_name, visualization_type, batch_id
            )
            
            # Store session data for client-side animation
            if result.get('wind_data'):
                app_state = get_app_state()
                app_state.active_sessions[job_id] = {
                    'file_path': str(file_path),
                    'wind_data': result['wind_data'],
                    'bounds': result.get('bounds'),
                    'center': result.get('center'),
                    'zoom': result.get('zoom'),
                    'created_at': datetime.now().isoformat(),
                    'batch_id': batch_id
                }
                result['session_id'] = job_id
            
            if create_tileset and settings.MAPBOX_TOKEN and settings.MAPBOX_USERNAME:
                # Start background tileset creation
                from app.services.background import create_mapbox_tileset_background
                background_tasks.add_task(
                    create_mapbox_tileset_background,
                    file_path,
                    job_id,
                    result.get('tileset_id'),
                    visualization_type,
                    batch_id
                )
                
                result['status'] = 'processing'
                result['message'] = f'File {file.filename} uploaded successfully. Creating Mapbox tileset...'
            
            results['files'].append({
                "filename": file.filename,
                "job_id": job_id,
                "success": True,
                **result
            })
            results['processed_files'] += 1
            
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            results['errors'].append({
                "filename": file.filename,
                "error": str(e)
            })
            
            # Clean up file on error
            if 'file_path' in locals() and file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass
    
    # Update overall status
    if results['processed_files'] == results['total_files']:
        results['status'] = 'completed'
    elif results['processed_files'] > 0:
        results['status'] = 'partial'
    else:
        results['status'] = 'failed'
    
    return results