"""
Page routes for the application
"""

from fastapi import Request, Depends
from fastapi.responses import HTMLResponse
from app.dependencies import get_settings, logger
from app.config import DEFAULT_TILESET
from app.core.mapbox_client import MapboxClient

async def get_main_page(request: Request, settings = Depends(get_settings)):
    """Main page with weather visualization"""
    from app.main import templates
    
    # Get list of available tilesets
    available_tilesets = []
    
    # Add default Mapbox weather data
    available_tilesets.append(DEFAULT_TILESET)
    
    # Add user's uploaded tilesets
    if settings.MAPBOX_TOKEN and settings.MAPBOX_USERNAME:
        try:
            client = MapboxClient()
            user_tilesets = client.list_tilesets(limit=50)
            
            for ts in user_tilesets:
                # Include weather-related tilesets
                tileset_name = ts.get('name', '').lower()
                tileset_id = ts.get('id', '')
                
                if any(keyword in tileset_name or keyword in tileset_id.lower() 
                      for keyword in ['weather', 'netcdf', 'wx_', 'wind', 'flow', 'raster']):
                    
                    tileset_info = {
                        "id": ts['id'],
                        "name": ts.get('name', ts['id']),
                        "type": "user",
                        "created": ts.get('created', ''),
                        "modified": ts.get('modified', '')
                    }
                    
                    # Check for recipe info
                    from app.core.recipe_manager import get_recipe_info
                    recipe_data = get_recipe_info(tileset_id)
                    
                    if recipe_data:
                        tileset_info.update({
                            'format': recipe_data.get('actual_format', recipe_data.get('format', 'vector')),
                            'source_layer': recipe_data.get('source_layer'),
                            'session_id': recipe_data.get('session_id'),
                            'requested_format': recipe_data.get('requested_format', 'vector'),
                            'use_client_animation': recipe_data.get('use_client_animation', False),
                            'bounds': recipe_data.get('bounds'),
                            'center': recipe_data.get('center'),
                            'zoom': recipe_data.get('zoom'),
                            'batch_id': recipe_data.get('batch_id')
                        })
                    else:
                        # Check if it's a raster tileset
                        if 'raster' in ts.get('type', '').lower():
                            tileset_info['format'] = 'raster-array'
                        else:
                            tileset_info['format'] = 'vector'
                    
                    available_tilesets.append(tileset_info)
                    
        except Exception as e:
            logger.error(f"Error fetching user tilesets: {e}")
    
    logger.info(f"Available tilesets: {len(available_tilesets)}")
    
    return templates.TemplateResponse("main_weather_map.html", {
        "request": request,
        "mapbox_token": settings.MAPBOX_PUBLIC_TOKEN,
        "mapbox_username": settings.MAPBOX_USERNAME,
        "available_tilesets": available_tilesets,
        "default_tileset": DEFAULT_TILESET,
        "max_batch_size": settings.MAX_BATCH_SIZE
    })