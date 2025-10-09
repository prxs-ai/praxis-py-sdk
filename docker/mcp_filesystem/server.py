#!/usr/bin/env python3
"""MCP Filesystem Server
Provides filesystem operations through Model Context Protocol
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# MCP Models
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Any
    method: str
    params: dict[str, Any] | None = None


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Any
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class MCPError(BaseModel):
    code: int
    message: str
    data: dict[str, Any] | None = None


# Tool parameter schemas
class WriteFileParams(BaseModel):
    filename: str = Field(description="Target file path relative to shared directory")
    content: str = Field(description="Content to write to the file")
    mode: str | None = Field(
        default="overwrite", description="Write mode: overwrite, append, create_only"
    )
    encoding: str | None = Field(default="utf-8", description="File encoding")


class ReadFileParams(BaseModel):
    filename: str = Field(description="Source file path relative to shared directory")
    encoding: str | None = Field(default="utf-8", description="File encoding")
    max_size: int | None = Field(
        default=10485760, description="Maximum file size to read (bytes)"
    )


class ListDirectoryParams(BaseModel):
    path: str | None = Field(
        default=".", description="Directory path relative to shared directory"
    )
    include_hidden: bool | None = Field(
        default=False, description="Include hidden files and directories"
    )
    recursive: bool | None = Field(default=False, description="List files recursively")


class CreateDirectoryParams(BaseModel):
    path: str = Field(description="Directory path relative to shared directory")
    create_parents: bool | None = Field(
        default=True, description="Create parent directories if they don't exist"
    )


# MCP Filesystem Server
class MCPFilesystemServer:
    def __init__(self, shared_dir: str = "/shared"):
        self.shared_dir = Path(shared_dir).resolve()
        self.shared_dir.mkdir(exist_ok=True)

        # Available tools
        self.tools = {
            "write_file": {
                "name": "write_file",
                "description": "Write content to a file in the shared directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Target file path relative to shared directory",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["overwrite", "append", "create_only"],
                            "default": "overwrite",
                        },
                        "encoding": {"type": "string", "default": "utf-8"},
                    },
                    "required": ["filename", "content"],
                },
            },
            "read_file": {
                "name": "read_file",
                "description": "Read content from a file in the shared directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Source file path relative to shared directory",
                        },
                        "encoding": {"type": "string", "default": "utf-8"},
                        "max_size": {"type": "integer", "default": 10485760},
                    },
                    "required": ["filename"],
                },
            },
            "list_directory": {
                "name": "list_directory",
                "description": "List files and directories in the shared directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "default": ".",
                            "description": "Directory path relative to shared directory",
                        },
                        "include_hidden": {"type": "boolean", "default": False},
                        "recursive": {"type": "boolean", "default": False},
                    },
                    "required": [],
                },
            },
            "create_directory": {
                "name": "create_directory",
                "description": "Create a new directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path relative to shared directory",
                        },
                        "create_parents": {"type": "boolean", "default": True},
                    },
                    "required": ["path"],
                },
            },
        }

    def _get_safe_path(self, relative_path: str) -> Path:
        """Get a safe path within the shared directory"""
        try:
            # Remove leading slash and resolve relative path
            clean_path = relative_path.lstrip("/")
            full_path = (self.shared_dir / clean_path).resolve()

            # Ensure the path is within shared directory
            if not str(full_path).startswith(str(self.shared_dir)):
                raise ValueError(f"Path '{relative_path}' is outside shared directory")

            return full_path
        except Exception as e:
            raise ValueError(f"Invalid path '{relative_path}': {str(e)}")

    async def write_file(self, params: WriteFileParams) -> dict[str, Any]:
        """Write content to a file"""
        try:
            file_path = self._get_safe_path(params.filename)

            # Check if file exists and mode is create_only
            if params.mode == "create_only" and file_path.exists():
                raise ValueError(
                    f"File '{params.filename}' already exists and mode is create_only"
                )

            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Determine write mode
            mode = "a" if params.mode == "append" else "w"

            # Write content
            with open(file_path, mode, encoding=params.encoding) as f:
                f.write(params.content)

            return {
                "success": True,
                "message": f"Successfully wrote to {params.filename}",
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "mode": params.mode,
            }

        except Exception as e:
            logger.error(f"Error writing file {params.filename}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def read_file(self, params: ReadFileParams) -> dict[str, Any]:
        """Read content from a file"""
        try:
            file_path = self._get_safe_path(params.filename)

            if not file_path.exists():
                raise ValueError(f"File '{params.filename}' does not exist")

            if not file_path.is_file():
                raise ValueError(f"'{params.filename}' is not a file")

            # Check file size
            file_size = file_path.stat().st_size
            if file_size > params.max_size:
                raise ValueError(
                    f"File size ({file_size} bytes) exceeds maximum allowed size ({params.max_size} bytes)"
                )

            # Read content
            with open(file_path, encoding=params.encoding) as f:
                content = f.read()

            return {
                "success": True,
                "content": content,
                "path": str(file_path),
                "size": file_size,
                "encoding": params.encoding,
            }

        except Exception as e:
            logger.error(f"Error reading file {params.filename}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def list_directory(self, params: ListDirectoryParams) -> dict[str, Any]:
        """List files and directories"""
        try:
            dir_path = self._get_safe_path(params.path)

            if not dir_path.exists():
                raise ValueError(f"Directory '{params.path}' does not exist")

            if not dir_path.is_dir():
                raise ValueError(f"'{params.path}' is not a directory")

            files = []

            if params.recursive:
                pattern = "**/*"
                paths = dir_path.rglob(pattern)
            else:
                paths = dir_path.iterdir()

            for path in paths:
                # Skip hidden files unless requested
                if not params.include_hidden and path.name.startswith("."):
                    continue

                try:
                    stat = path.stat()
                    relative_path = path.relative_to(self.shared_dir)

                    file_info = {
                        "name": path.name,
                        "path": str(relative_path),
                        "type": "directory" if path.is_dir() else "file",
                        "size": stat.st_size if path.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "permissions": oct(stat.st_mode)[-3:],
                    }
                    files.append(file_info)

                except (OSError, PermissionError) as e:
                    logger.warning(f"Cannot access {path}: {str(e)}")
                    continue

            return {
                "success": True,
                "files": sorted(files, key=lambda x: (x["type"], x["name"])),
                "path": str(dir_path),
                "count": len(files),
            }

        except Exception as e:
            logger.error(f"Error listing directory {params.path}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def create_directory(self, params: CreateDirectoryParams) -> dict[str, Any]:
        """Create a new directory"""
        try:
            dir_path = self._get_safe_path(params.path)

            if dir_path.exists():
                if dir_path.is_dir():
                    return {
                        "success": True,
                        "message": f"Directory '{params.path}' already exists",
                        "path": str(dir_path),
                        "created": False,
                    }
                raise ValueError(f"Path '{params.path}' exists but is not a directory")

            # Create directory
            dir_path.mkdir(parents=params.create_parents, exist_ok=True)

            return {
                "success": True,
                "message": f"Successfully created directory '{params.path}'",
                "path": str(dir_path),
                "created": True,
            }

        except Exception as e:
            logger.error(f"Error creating directory {params.path}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))


# FastAPI app
app = FastAPI(title="MCP Filesystem Server", version="1.0.0")
server = MCPFilesystemServer(os.getenv("MCP_SHARED_DIR", "/shared"))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "server": "mcp-filesystem", "version": "1.0.0"}


@app.get("/capabilities")
async def get_capabilities():
    """Get server capabilities"""
    return {
        "capabilities": {"tools": server.tools},
        "serverInfo": {"name": "mcp-filesystem", "version": "1.0.0"},
    }


@app.post("/mcp")
async def handle_mcp_request(request: MCPRequest):
    """Handle MCP requests"""
    try:
        method = request.method
        params = request.params or {}

        if method == "tools/list":
            return MCPResponse(
                id=request.id, result={"tools": list(server.tools.values())}
            )

        if method == "tools/call":
            tool_name = params.get("name")
            tool_arguments = params.get("arguments", {})

            if tool_name == "write_file":
                result = await server.write_file(WriteFileParams(**tool_arguments))
            elif tool_name == "read_file":
                result = await server.read_file(ReadFileParams(**tool_arguments))
            elif tool_name == "list_directory":
                result = await server.list_directory(
                    ListDirectoryParams(**tool_arguments)
                )
            elif tool_name == "create_directory":
                result = await server.create_directory(
                    CreateDirectoryParams(**tool_arguments)
                )
            else:
                return MCPResponse(
                    id=request.id,
                    error=MCPError(
                        code=-32601, message=f"Unknown tool: {tool_name}"
                    ).dict(),
                )

            return MCPResponse(
                id=request.id,
                result={
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                },
            )

        return MCPResponse(
            id=request.id,
            error=MCPError(code=-32601, message=f"Unknown method: {method}").dict(),
        )

    except Exception as e:
        logger.error(f"Error handling MCP request: {str(e)}")
        return MCPResponse(
            id=request.id, error=MCPError(code=-32603, message=str(e)).dict()
        )


if __name__ == "__main__":
    port = int(os.getenv("MCP_SERVER_PORT", 3000))
    logger.info(f"Starting MCP Filesystem Server on port {port}")
    logger.info(f"Shared directory: {server.shared_dir}")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
