"""
Tileset-related API endpoints
"""

from fastapi import APIRouter, HTTPException, Form
from app.dependencies import settings, logger
from app.core.mapbox_client import MapboxClient

router = APIRouter()


@router.post("/load-tileset")
async def load_tileset(tileset_id: str = Form(...)):
    """Load a specific tileset for visualization"""
    try:
        # Check if it's a default tileset
        from app.config import DEFAULT_TILESET
        if tileset_id == DEFAULT_TILESET['id']:
            return {
                "success": True,
                "tileset_id": tileset_id,
                "type": "default",
                "format": "raster-array",
                "actual_format": "raster-array",
                "config": {
                    "layers": ["wind"],
                    "wind_source": tileset_id,
                    "source_layer": "10winds"
                }
            }
        
        # For user tilesets, check for recipe
        from app.core.recipe_manager import get_recipe_info
        recipe_data = get_recipe_info(tileset_id)
        
        format_type = 'vector'  # Default
        actual_format = 'vector'
        requested_format = 'vector'
        source_layer = 'weather_data'
        
        if recipe_data:
            format_type = recipe_data.get('format', 'vector')
            actual_format = recipe_data.get('actual_format', format_type)
            requested_format = recipe_data.get('requested_format', format_type)
            source_layer = recipe_data.get('source_layer', 'weather_data')
        
        # Check if tileset exists on Mapbox
        if settings.MAPBOX_TOKEN:
            client = MapboxClient()
            tileset_info = client.check_tileset_format(tileset_id)
            
            if tileset_info.get('success'):
                actual_format = tileset_info.get('format', actual_format)
                if actual_format == 'raster-array':
                    source_layer = '10winds'
                else:
                    source_layer = 'weather_data'
        
        return {
            "success": True,
            "tileset_id": tileset_id,
            "type": "user",
            "format": actual_format,
            "actual_format": actual_format,
            "requested_format": requested_format,
            "config": {
                "source_layer": source_layer,
                "visualization_type": recipe_data.get('visualization_type', 'vector') if recipe_data else 'vector',
                "scalar_vars": recipe_data.get('scalar_vars', []) if recipe_data else [],
                "vector_pairs": recipe_data.get('vector_pairs', []) if recipe_data else [],
                "format": actual_format,
                "is_raster_array": actual_format == 'raster-array',
                "use_client_animation": recipe_data.get('use_client_animation', False) if recipe_data else False,
                "session_id": recipe_data.get('session_id') if recipe_data else None,
                "bounds": recipe_data.get('bounds') if recipe_data else None,
                "center": recipe_data.get('center') if recipe_data else None,
                "zoom": recipe_data.get('zoom') if recipe_data else None,
                "batch_id": recipe_data.get('batch_id') if recipe_data else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error loading tileset: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/tileset-status/{username}/{tileset_id}")
async def get_tileset_publish_status(username: str, tileset_id: str):
    """Check the publish status of a tileset"""
    if not settings.MAPBOX_TOKEN:
        raise HTTPException(500, "Mapbox token not configured")
    
    try:
        client = MapboxClient()
        status = client.tileset_manager.get_tileset_status(tileset_id)
        
        # Check for any active publishing jobs
        if 'publishing' in status:
            return {
                "status": "publishing",
                "complete": False
            }
        
        return {
            "status": "ready",
            "complete": True,
            "tileset_info": status
        }
        
    except Exception as e:
        logger.error(f"Error getting tileset status: {e}")
        return {
            "status": "error",
            "error": str(e)
        }