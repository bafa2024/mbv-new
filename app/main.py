"""
Main FastAPI application
"""

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Fix for Windows path issues
if sys.platform == "win32":
    import pathlib
    temp = pathlib.PosixPath
    pathlib.PosixPath = pathlib.WindowsPath

from app.config import settings
from app.dependencies import logger
from app.api import files, upload, visualization, tileset, dataset, batch
from app.core.file_manager import load_file_database
from app.utils.cleanup import cleanup_old_files

# Create FastAPI app
app = FastAPI(
    title="Weather Visualization Platform",
    version="5.0.0",
    description="Process and visualize NetCDF weather data using Mapbox"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if settings.STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")
else:
    logger.warning(f"Static directory not found: {settings.STATIC_DIR}")

# Templates
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

# Include routers
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(visualization.router, prefix="/api", tags=["visualization"])
app.include_router(tileset.router, prefix="/api", tags=["tileset"])
app.include_router(dataset.router, prefix="/api", tags=["dataset"])
app.include_router(batch.router, prefix="/api", tags=["batch"])


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info(f"Starting Weather Visualization Platform v5.0...")
    logger.info(f"Mapbox Username: {settings.MAPBOX_USERNAME}")
    logger.info(f"Mapbox Token Set: {'Yes' if settings.MAPBOX_TOKEN else 'No'}")
    
    # Load file database
    load_file_database()
    
    # Run cleanup
    await cleanup_old_files()
    
    # Test Mapbox connection
    if settings.MAPBOX_TOKEN and settings.MAPBOX_USERNAME:
        try:
            from app.core.mapbox_client import MapboxClient
            client = MapboxClient()
            tilesets = client.list_tilesets(limit=1)
            logger.info(f"Mapbox connection successful. Found {len(tilesets)} tilesets.")
        except Exception as e:
            logger.error(f"Mapbox connection test failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Weather Visualization Platform...")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from app.dependencies import app_state
    
    return {
        "status": "healthy",
        "mapbox_configured": bool(settings.MAPBOX_TOKEN and settings.MAPBOX_USERNAME),
        "active_jobs": len(app_state.active_visualizations),
        "active_sessions": len(app_state.active_sessions),
        "version": "5.0.0"
    }


# Main page route
from fastapi import Request
from fastapi.responses import HTMLResponse
from app.api.pages import get_main_page

app.add_api_route("/", get_main_page, methods=["GET"], response_class=HTMLResponse)