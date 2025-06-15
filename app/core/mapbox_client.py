"""
Mapbox API client wrapper
"""

from typing import Dict, List, Any, Optional
from app.dependencies import settings, logger
from tileset_management import MapboxTilesetManager
from mts_raster_manager import MTSRasterManager
from mapbox_dataset_manager import MapboxDatasetManager


class MapboxClient:
    """Unified Mapbox client for all operations"""
    
    def __init__(self):
        self.token = settings.MAPBOX_TOKEN
        self.username = settings.MAPBOX_USERNAME
        
        # Initialize managers
        self.tileset_manager = MapboxTilesetManager(self.token, self.username)
        self.raster_manager = MTSRasterManager(self.token, self.username)
        self.dataset_manager = MapboxDatasetManager(self.token, self.username)
    
    def list_tilesets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List user's tilesets"""
        return self.tileset_manager.list_tilesets(limit)
    
    def create_tileset_from_netcdf(
        self,
        netcdf_path: str,
        tileset_id: str,
        format_type: str = "vector"
    ) -> Dict[str, Any]:
        """Create a tileset from NetCDF file"""
        if format_type == "raster-array":
            return self.raster_manager.create_raster_tileset(netcdf_path, tileset_id)
        else:
            return self.tileset_manager.process_netcdf_to_tileset(netcdf_path, tileset_id)
    
    def check_tileset_format(self, tileset_id: str) -> Dict[str, Any]:
        """Check the format of an existing tileset"""
        return self.tileset_manager.check_tileset_format(tileset_id)
    
    def create_dataset_from_netcdf(
        self,
        netcdf_path: str,
        dataset_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a dataset from NetCDF file"""
        return self.dataset_manager.process_netcdf_to_dataset(netcdf_path, dataset_name)
    
    def list_datasets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List user's datasets"""
        return self.dataset_manager.list_datasets(limit)
    
    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset"""
        return self.dataset_manager.delete_dataset(dataset_id)