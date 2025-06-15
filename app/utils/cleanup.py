"""
File cleanup utilities
"""

from datetime import datetime
from app.dependencies import settings, logger, get_app_state


async def cleanup_old_files():
    """Remove old temporary files and sessions"""
    try:
        cutoff_time = datetime.now().timestamp() - (24 * 3600)  # 24 hours
        
        for dir_path in [settings.UPLOAD_DIR, settings.PROCESSED_DIR]:
            for file_path in dir_path.glob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    # Check if file is still in use
                    file_id = file_path.stem.split('_')[0]
                    app_state = get_app_state()
                    
                    if file_id not in app_state.uploaded_files and file_id not in app_state.active_visualizations:
                        file_path.unlink()
                        logger.info(f"Cleaned up old file: {file_path}")
        
        # Clean up old sessions
        app_state = get_app_state()
        to_remove = []
        
        for session_id, session_data in app_state.active_sessions.items():
            created_at = datetime.fromisoformat(session_data.get('created_at', datetime.now().isoformat()))
            if (datetime.now() - created_at).total_seconds() > 24 * 3600:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del app_state.active_sessions[session_id]
            logger.info(f"Cleaned up old session: {session_id}")
        
        # Clean up old batch jobs
        to_remove = []
        for batch_id, batch_data in app_state.batch_jobs.items():
            created_at = datetime.fromisoformat(batch_data.get('created_at', datetime.now().isoformat()))
            if (datetime.now() - created_at).total_seconds() > 24 * 3600:
                to_remove.append(batch_id)
        
        for batch_id in to_remove:
            del app_state.batch_jobs[batch_id]
            logger.info(f"Cleaned up old batch job: {batch_id}")
                    
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")