"""
Static File Server for Frontend Integration.

This module provides static file serving capabilities for the
React frontend, including reports, assets, and file uploads/downloads.
"""

import mimetypes
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from uuid import uuid4

from fastapi import UploadFile, File, HTTPException, status, Request, Response
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from loguru import logger
from pydantic import BaseModel

from praxis_sdk.config import load_config


class FileUploadResponse(BaseModel):
    """Response for file upload operations."""
    success: bool
    filename: str
    size: int
    uploadId: str
    downloadUrl: str
    timestamp: str


class FileListResponse(BaseModel):
    """Response for file listing operations."""
    files: List[Dict[str, Any]]
    total: int
    directory: str


class StaticFileServer:
    """Static file server with upload/download capabilities."""
    
    def __init__(self):
        self.config = load_config()
        self._setup_directories()
    
    def _setup_directories(self):
        """Setup static file directories."""
        # Default directories - use temp dir if /app is not writable
        import os
        base_path = os.environ.get('PRAXIS_SHARED_PATH', '/app/shared')
        if not os.path.exists('/app') or not os.access('/app', os.W_OK):
            base_path = os.environ.get('PRAXIS_SHARED_PATH', '/tmp/praxis_shared')
        
        self.base_dir = Path(base_path)
        self.reports_dir = self.base_dir / "reports"
        self.assets_dir = self.base_dir / "assets"
        self.uploads_dir = self.base_dir / "uploads"
        self.temp_dir = self.base_dir / "temp"
        
        # Create directories if they don't exist
        for directory in [self.reports_dir, self.assets_dir, self.uploads_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Static directory ready: {directory}")
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get file information."""
        try:
            stat = file_path.stat()
            return {
                "name": file_path.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z",
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat() + "Z",
                "is_directory": file_path.is_dir(),
                "extension": file_path.suffix,
                "mime_type": mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            }
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return {}
    
    async def serve_file(self, file_path: str, directory_type: str = "reports") -> FileResponse:
        """Serve static file with proper headers."""
        try:
            # Determine base directory
            if directory_type == "reports":
                base_dir = self.reports_dir
            elif directory_type == "assets":
                base_dir = self.assets_dir
            elif directory_type == "uploads":
                base_dir = self.uploads_dir
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid directory type: {directory_type}"
                )
            
            # Construct full path
            full_path = base_dir / file_path
            
            # Security check - ensure path is within base directory
            try:
                full_path.resolve().relative_to(base_dir.resolve())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Path traversal detected"
                )
            
            # Check if file exists
            if not full_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {file_path}"
                )
            
            # Check if it's a file (not directory)
            if not full_path.is_file():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Path is not a file: {file_path}"
                )
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(str(full_path))
            if not content_type:
                content_type = "application/octet-stream"
            
            # Return file response with appropriate headers
            return FileResponse(
                path=str(full_path),
                media_type=content_type,
                filename=full_path.name,
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "X-File-Path": file_path,
                    "X-Directory-Type": directory_type
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error serving file {file_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error serving file: {str(e)}"
            )
    
    async def upload_file(self, file: UploadFile, directory_type: str = "uploads") -> FileUploadResponse:
        """Handle file upload."""
        try:
            # Determine target directory
            if directory_type == "uploads":
                target_dir = self.uploads_dir
            elif directory_type == "reports":
                target_dir = self.reports_dir
            elif directory_type == "assets":
                target_dir = self.assets_dir
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid directory type: {directory_type}"
                )
            
            # Generate unique filename to avoid conflicts
            upload_id = str(uuid4())
            file_extension = Path(file.filename).suffix if file.filename else ""
            safe_filename = f"{upload_id}_{file.filename}" if file.filename else f"{upload_id}{file_extension}"
            target_path = target_dir / safe_filename
            
            # Read and save file
            file_content = await file.read()
            file_size = len(file_content)
            
            with open(target_path, "wb") as f:
                f.write(file_content)
            
            # Generate download URL
            download_url = f"/{directory_type}/{safe_filename}"
            
            logger.info(f"File uploaded successfully: {safe_filename} ({file_size} bytes)")
            
            return FileUploadResponse(
                success=True,
                filename=safe_filename,
                size=file_size,
                uploadId=upload_id,
                downloadUrl=download_url,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading file: {str(e)}"
            )
    
    async def list_files(self, directory_type: str = "reports", subdirectory: str = "") -> FileListResponse:
        """List files in directory."""
        try:
            # Determine base directory
            if directory_type == "reports":
                base_dir = self.reports_dir
            elif directory_type == "assets":
                base_dir = self.assets_dir
            elif directory_type == "uploads":
                base_dir = self.uploads_dir
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid directory type: {directory_type}"
                )
            
            # Construct target directory
            if subdirectory:
                target_dir = base_dir / subdirectory
                # Security check
                try:
                    target_dir.resolve().relative_to(base_dir.resolve())
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Path traversal detected"
                    )
            else:
                target_dir = base_dir
            
            # Check if directory exists
            if not target_dir.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Directory not found: {subdirectory}"
                )
            
            if not target_dir.is_dir():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Path is not a directory: {subdirectory}"
                )
            
            # List files and directories
            files_info = []
            for item in target_dir.iterdir():
                try:
                    file_info = self.get_file_info(item)
                    if file_info:
                        # Add download URL for files
                        if not item.is_dir():
                            relative_path = item.relative_to(base_dir)
                            file_info["downloadUrl"] = f"/{directory_type}/{relative_path}"
                        files_info.append(file_info)
                except Exception as e:
                    logger.warning(f"Error processing file {item}: {e}")
                    continue
            
            # Sort by name
            files_info.sort(key=lambda x: (not x.get("is_directory", False), x.get("name", "")))
            
            return FileListResponse(
                files=files_info,
                total=len(files_info),
                directory=str(target_dir.relative_to(base_dir)) if subdirectory else ""
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error listing files in {directory_type}/{subdirectory}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error listing files: {str(e)}"
            )
    
    async def delete_file(self, file_path: str, directory_type: str = "uploads") -> Dict[str, Any]:
        """Delete file."""
        try:
            # Determine base directory
            if directory_type == "uploads":
                base_dir = self.uploads_dir
            elif directory_type == "reports":
                base_dir = self.reports_dir
            elif directory_type == "assets":
                base_dir = self.assets_dir
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid directory type: {directory_type}"
                )
            
            # Construct full path
            full_path = base_dir / file_path
            
            # Security check
            try:
                full_path.resolve().relative_to(base_dir.resolve())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Path traversal detected"
                )
            
            # Check if file exists
            if not full_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {file_path}"
                )
            
            # Delete file
            if full_path.is_file():
                full_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return {
                    "success": True,
                    "message": f"File {file_path} deleted successfully",
                    "deletedAt": datetime.utcnow().isoformat() + "Z"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Path is not a file: {file_path}"
                )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting file: {str(e)}"
            )
    
    async def create_sample_files(self):
        """Create sample files for testing."""
        try:
            # Sample report file
            sample_report_path = self.reports_dir / "sample_analysis.json"
            sample_report_data = {
                "title": "Sample Analysis Report",
                "generated": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "processed_items": 42,
                    "success_rate": 95.5,
                    "errors": 2
                },
                "metadata": {
                    "agent": "Praxis Python Agent",
                    "version": "1.0.0"
                }
            }
            
            with open(sample_report_path, "w") as f:
                import json
                json.dump(sample_report_data, f, indent=2)
            
            # Sample text file
            sample_text_path = self.reports_dir / "readme.txt"
            sample_text_content = """
# Praxis Reports Directory

This directory contains generated reports from workflow executions.

Files here can be downloaded via the API endpoints:
- GET /reports/{filename} - Download specific report
- GET /api/files/list?directory=reports - List all reports
- POST /api/upload - Upload new files

Generated by Praxis Python SDK
""".strip()
            
            with open(sample_text_path, "w") as f:
                f.write(sample_text_content)
            
            logger.info("Sample files created successfully")
            
        except Exception as e:
            logger.error(f"Error creating sample files: {e}")


# Global static file server instance
static_file_server = StaticFileServer()


class StaticFileHandlers:
    """Static file API handlers."""
    
    @staticmethod
    async def serve_report_file(filename: str) -> FileResponse:
        """Serve file from reports directory."""
        return await static_file_server.serve_file(filename, "reports")
    
    @staticmethod
    async def serve_asset_file(filename: str) -> FileResponse:
        """Serve file from assets directory."""
        return await static_file_server.serve_file(filename, "assets")
    
    @staticmethod
    async def serve_upload_file(filename: str) -> FileResponse:
        """Serve file from uploads directory."""
        return await static_file_server.serve_file(filename, "uploads")
    
    @staticmethod
    async def upload_file(file: UploadFile = File(...), directory: str = "uploads") -> FileUploadResponse:
        """Handle file upload."""
        return await static_file_server.upload_file(file, directory)
    
    @staticmethod
    async def list_files(directory: str = "reports", subdirectory: str = "") -> FileListResponse:
        """List files in directory."""
        return await static_file_server.list_files(directory, subdirectory)
    
    @staticmethod
    async def delete_file(filename: str, directory: str = "uploads") -> Dict[str, Any]:
        """Delete file."""
        return await static_file_server.delete_file(filename, directory)
    
    @staticmethod
    async def get_file_info(filename: str, directory: str = "reports") -> Dict[str, Any]:
        """Get file information."""
        try:
            # Determine base directory
            if directory == "reports":
                base_dir = static_file_server.reports_dir
            elif directory == "assets":
                base_dir = static_file_server.assets_dir
            elif directory == "uploads":
                base_dir = static_file_server.uploads_dir
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid directory type: {directory}"
                )
            
            file_path = base_dir / filename
            
            # Security check
            try:
                file_path.resolve().relative_to(base_dir.resolve())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Path traversal detected"
                )
            
            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {filename}"
                )
            
            file_info = static_file_server.get_file_info(file_path)
            file_info["downloadUrl"] = f"/{directory}/{filename}"
            
            return file_info
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file info for {filename}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting file info: {str(e)}"
            )


# Export handlers instance
static_file_handlers = StaticFileHandlers()