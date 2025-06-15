"""
File upload API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from app.dependencies import get_app_state, settings, logger
from app.models.upload import UploadResponse, BatchUploadResponse
from app.services.processing import process_batch_upload
from app.core.validators import validate_netcdf_file
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/upload-netcdf", response_model=UploadResponse)
async def upload_netcdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    create_tileset: bool = Form(True),
    tileset_name: Optional[str] = Form(None),
    visualization_type: str = Form("vector")
):
    """Upload and process single NetCDF file"""
    
    # Validate file
    validation = validate_netcdf_file(file)
    if not validation['valid']:
        raise HTTPException(400, validation['error'])
    
    # Check file size
    content = await file.read()
    file_size = len(content)
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Maximum size is {settings.MAX_FILE_SIZE / 1024 / 1024}MB")
    
    # Create job
    job_id = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Process single file using batch logic
    files = [{"file": file, "content": content}]
    result = await process_batch_upload(
        files=files,
        job_ids=[job_id],
        create_tileset=create_tileset,
        tileset_names=[tileset_name] if tileset_name else None,
        visualization_type=visualization_type,
        background_tasks=background_tasks
    )
    
    # Update file database
    app_state = get_app_state()
    if result['files']:
        file_result = result['files'][0]
        if file_result.get('success'):
            app_state.uploaded_files[job_id] = {
                "id": job_id,
                "filename": f"{job_id}_{file.filename}",
                "original_filename": file.filename,
                "size": file_size,
                "upload_date": datetime.now().isoformat(),
                "status": "active",
                "metadata": file_result.get('metadata'),
                "tileset_id": file_result.get('tileset_id'),
                "job_id": job_id,
                "processing_status": file_result.get('status', 'processing'),
                "file_path": str(settings.UPLOAD_DIR / f"{job_id}_{file.filename}")
            }
    
    # Return single file result
    if result['files']:
        return result['files'][0]
    else:
        raise HTTPException(500, "Failed to process file")


@router.post("/upload-netcdf-batch", response_model=BatchUploadResponse)
async def upload_netcdf_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    create_tileset: bool = Form(True),
    tileset_names: Optional[str] = Form(None),
    visualization_type: str = Form("vector"),
    merge_files: bool = Form(False)
):
    """Upload and process multiple NetCDF files"""
    
    # Validate batch size
    if len(files) > settings.MAX_BATCH_SIZE:
        raise HTTPException(400, f"Too many files. Maximum batch size is {settings.MAX_BATCH_SIZE}")
    
    # Validate all files
    for file in files:
        validation = validate_netcdf_file(file)
        if not validation['valid']:
            raise HTTPException(400, f"{file.filename}: {validation['error']}")
    
    # Create batch ID
    batch_id = str(uuid.uuid4())
    
    # Parse tileset names
    tileset_name_list = None
    if tileset_names:
        tileset_name_list = [name.strip() for name in tileset_names.split(',')]
        if len(tileset_name_list) != len(files):
            tileset_name_list = None
    
    # Read all files
    file_contents = []
    job_ids = []
    
    for i, file in enumerate(files):
        content = await file.read()
        
        # Check individual file size
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(400, f"File {file.filename} too large. Maximum size is {settings.MAX_FILE_SIZE / 1024 / 1024}MB")
        
        job_id = f"{batch_id}_{i}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        job_ids.append(job_id)
        file_contents.append({"file": file, "content": content})
    
    # Initialize batch job
    app_state = get_app_state()
    app_state.batch_jobs[batch_id] = {
        "batch_id": batch_id,
        "total_files": len(files),
        "processed_files": 0,
        "status": "processing",
        "files": [],
        "errors": [],
        "created_at": datetime.now().isoformat()
    }
    
    # Process files
    result = await process_batch_upload(
        files=file_contents,
        job_ids=job_ids,
        create_tileset=create_tileset,
        tileset_names=tileset_name_list,
        visualization_type=visualization_type,
        background_tasks=background_tasks,
        batch_id=batch_id
    )
    
    # Update batch job status
    app_state.batch_jobs[batch_id].update(result)
    
    # Update file database
    for i, file_result in enumerate(result.get('files', [])):
        if file_result.get('success'):
            job_id = job_ids[i]
            file = files[i]
            app_state.uploaded_files[job_id] = {
                "id": job_id,
                "filename": f"{job_id}_{file.filename}",
                "original_filename": file.filename,
                "size": len(file_contents[i]['content']),
                "upload_date": datetime.now().isoformat(),
                "status": "active",
                "metadata": file_result.get('metadata'),
                "tileset_id": file_result.get('tileset_id'),
                "job_id": job_id,
                "processing_status": file_result.get('status', 'processing'),
                "batch_id": batch_id,
                "file_path": str(settings.UPLOAD_DIR / f"{job_id}_{file.filename}")
            }
    
    return result