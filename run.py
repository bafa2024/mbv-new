#!/usr/bin/env python3
"""
Application runner script
"""

import uvicorn
import os
from app.config import settings

if __name__ == "__main__":
    # Get configuration from environment or settings
    host = os.getenv("HOST", settings.HOST)
    port = int(os.getenv("PORT", settings.PORT))
    reload = settings.DEBUG
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=settings.LOG_LEVEL.lower()
    )