"""
Background task services
"""

import os
import time
from pathlib import Path
from typing import Optional
from app.dependencies import settings, logger, get_app_state
from app.core.mapbox_client import MapboxClient
from app.core.recipe_manager import save_recipe_info


async def create_mapbox_tileset_background(
    file_path: Path,
    job_id: str,
    tileset_id: str,
    visualization_type: str,
    batch_id: Optional[str] = None
):
    """Background task to create Mapbox tileset with proper error handling"""
    app_state = get_app_state()
    
    try:
        if not settings.MAPBOX_TOKEN:
            logger.error("Mapbox token not configured")
            if job_id in app_state.active_visualizations:
                app_state.active_visualizations[job_id]['status'] = 'failed'
                app_state.active_visualizations[job_id]['error'] = 'Mapbox token not configured'
            # Update file database
            if job_id in app_state.uploaded_files:
                app_state.uploaded_files[job_id]['processing_status'] = 'failed'
                app_state.uploaded_files[job_id]['error'] = 'Mapbox token not configured'
            return
        
        # Convert Path to string
        file_path_str = str(file_path)
        
        # Verify file exists
        if not os.path.exists(file_path_str):
            logger.error(f"NetCDF file not found: {file_path_str}")
            if job_id in app_state.active_visualizations:
                app_state.active_visualizations[job_id]['status'] = 'failed'
                app_state.active_visualizations[job_id]['error'] = 'Input file not found'
            # Update file database
            if job_id in app_state.uploaded_files:
                app_state.uploaded_files[job_id]['processing_status'] = 'failed'
                app_state.uploaded_files[job_id]['error'] = 'Input file not found'
            return
        
        # Get the requested format
        requested_format = app_state.active_visualizations[job_id].get('requested_format', 'vector')
        
        logger.info(f"Creating {requested_format} tileset from {file_path_str}")
        
        # Create Mapbox client
        client = MapboxClient()
        
        # Initialize variables
        actual_format = None
        result = None
        
        # Check if raster-array was requested
        if requested_format == 'raster-array' and settings.MAPBOX_TOKEN:
            logger.info("Attempting to create raster-array tileset...")
            
            # Try to create raster tileset
            result = await client.raster_manager.create_raster_tileset(file_path_str, tileset_id)
            
            if result['success']:
                actual_format = 'raster-array'
                # Update visualization info
                if job_id in app_state.active_visualizations:
                    app_state.active_visualizations[job_id].update({
                        'mapbox_tileset': result['tileset_id'],
                        'status': 'completed',
                        'format': 'raster-array',
                        'actual_format': 'raster-array',
                        'requested_format': 'raster-array',
                        'source_layer': result.get('source_layer', '10winds'),
                        'recipe_id': result.get('recipe_id'),
                        'publish_job_id': result.get('publish_job_id')
                    })
                    
                    # Save recipe info
                    save_recipe_info(tileset_id, result, app_state.active_visualizations[job_id])
                
                # Update file database
                if job_id in app_state.uploaded_files:
                    app_state.uploaded_files[job_id]['processing_status'] = 'completed'
                    app_state.uploaded_files[job_id]['tileset_id'] = result['tileset_id']
                    
                logger.info("Successfully created raster-array tileset")
                
                # Update batch job if part of batch
                if batch_id and batch_id in app_state.batch_jobs:
                    for file_info in app_state.batch_jobs[batch_id]['files']:
                        if file_info.get('job_id') == job_id:
                            file_info['status'] = 'completed'
                            break
                
                return
            else:
                # Check if it's a Pro account issue
                if result.get('fallback_to_vector', False) or result.get('error_code') == 422:
                    logger.warning("Raster-array requires Pro account, falling back to vector")
                    if job_id in app_state.active_visualizations:
                        app_state.active_visualizations[job_id]['warning'] = result.get('error', 'Falling back to vector format')
                        app_state.active_visualizations[job_id]['use_client_animation'] = True
                    actual_format = 'vector'  # Will fall back to vector
                else:
                    # Some other error occurred
                    logger.error(f"Raster tileset creation failed: {result.get('error')}")
                    if job_id in app_state.active_visualizations:
                        app_state.active_visualizations[job_id]['error'] = result.get('error')
                        app_state.active_visualizations[job_id]['status'] = 'failed'
                    
                    # Update file database
                    if job_id in app_state.uploaded_files:
                        app_state.uploaded_files[job_id]['processing_status'] = 'failed'
                        app_state.uploaded_files[job_id]['error'] = result.get('error')
                    
                    # Update batch job if part of batch
                    if batch_id and batch_id in app_state.batch_jobs:
                        for file_info in app_state.batch_jobs[batch_id]['files']:
                            if file_info.get('job_id') == job_id:
                                file_info['status'] = 'failed'
                                file_info['error'] = result.get('error')
                                break
                    
                    return
        
        # Fall back to vector format (or if vector was requested)
        if actual_format != 'raster-array':
            logger.info("Creating vector tileset...")
            
            # Process NetCDF to tileset
            result = client.tileset_manager.process_netcdf_to_tileset(file_path_str, tileset_id)
            
            if result['success']:
                actual_format = 'vector'
                # Update visualization info
                if job_id in app_state.active_visualizations:
                    app_state.active_visualizations[job_id].update({
                        'mapbox_tileset': result['tileset_id'],
                        'status': 'completed',
                        'format': 'vector',
                        'actual_format': 'vector',
                        'source_layer': result.get('source_layer', 'weather_data'),
                        'recipe_id': result.get('recipe_id'),
                        'publish_job_id': result.get('publish_job_id')
                    })
                    
                    # Add warning if raster was requested but vector was created
                    if requested_format == 'raster-array':
                        app_state.active_visualizations[job_id]['format_fallback'] = True
                        app_state.active_visualizations[job_id]['warning'] = 'Created vector format (raster-array requires Pro account)'
                        app_state.active_visualizations[job_id]['use_client_animation'] = True
                    
                    # Save recipe info
                    save_recipe_info(tileset_id, result, app_state.active_visualizations[job_id])
                
                # Update file database
                if job_id in app_state.uploaded_files:
                    app_state.uploaded_files[job_id]['processing_status'] = 'completed'
                    app_state.uploaded_files[job_id]['tileset_id'] = result['tileset_id']
                
                # Update batch job if part of batch
                if batch_id and batch_id in app_state.batch_jobs:
                    for file_info in app_state.batch_jobs[batch_id]['files']:
                        if file_info.get('job_id') == job_id:
                            file_info['status'] = 'completed'
                            break
                        
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"Tileset creation failed: {error_msg}")
                
                if job_id in app_state.active_visualizations:
                    app_state.active_visualizations[job_id]['status'] = 'failed'
                    app_state.active_visualizations[job_id]['error'] = error_msg
                
                # Update file database
                if job_id in app_state.uploaded_files:
                    app_state.uploaded_files[job_id]['processing_status'] = 'failed'
                    app_state.uploaded_files[job_id]['error'] = error_msg
                
                # Update batch job if part of batch
                if batch_id and batch_id in app_state.batch_jobs:
                    for file_info in app_state.batch_jobs[batch_id]['files']:
                        if file_info.get('job_id') == job_id:
                            file_info['status'] = 'failed'
                            file_info['error'] = error_msg
                            break
                
    except Exception as e:
        logger.error(f"Error creating tileset: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if job_id in app_state.active_visualizations:
            app_state.active_visualizations[job_id]['status'] = 'failed'
            app_state.active_visualizations[job_id]['error'] = str(e)
        
        # Update file database
        if job_id in app_state.uploaded_files:
            app_state.uploaded_files[job_id]['processing_status'] = 'failed'
            app_state.uploaded_files[job_id]['error'] = str(e)
        
        # Update batch job if part of batch
        if batch_id and batch_id in app_state.batch_jobs:
            for file_info in app_state.batch_jobs[batch_id]['files']:
                if file_info.get('job_id') == job_id:
                    file_info['status'] = 'failed'
                    file_info['error'] = str(e)
                    break