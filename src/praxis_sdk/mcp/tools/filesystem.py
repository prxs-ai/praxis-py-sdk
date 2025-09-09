"""
MCP Filesystem Tools Implementation

Implementation of MCP filesystem tools with security validation,
shared directory integration, and proper error handling.
"""

import os
import shutil
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger
import json
import stat
from datetime import datetime

from praxis_sdk.config import load_config


class SecurityError(Exception):
    """Exception raised for security violations"""
    pass


class FilesystemTools:
    """
    MCP filesystem tools implementation with security validation
    and integration with the shared directory system
    """
    
    def __init__(self):
        config = load_config()
        self.shared_dir = Path(config.agent.shared_dir).resolve()
        self.allowed_paths = [self.shared_dir]
        
        # Ensure shared directory exists
        self.shared_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized FilesystemTools with shared dir: {self.shared_dir}")
    
    def _validate_path(self, path_str: str) -> Path:
        """
        Validate and resolve path to ensure it's within allowed directories
        
        Args:
            path_str: Path string to validate
            
        Returns:
            Resolved Path object
            
        Raises:
            SecurityError: If path is outside allowed directories
        """
        try:
            # Convert to absolute path
            if not os.path.isabs(path_str):
                # Relative paths are resolved against shared directory
                path = (self.shared_dir / path_str).resolve()
            else:
                path = Path(path_str).resolve()
            
            # Check if path is within allowed directories
            is_allowed = False
            for allowed_path in self.allowed_paths:
                try:
                    path.relative_to(allowed_path)
                    is_allowed = True
                    break
                except ValueError:
                    continue
            
            if not is_allowed:
                raise SecurityError(
                    f"Access denied: Path '{path}' is outside allowed directories. "
                    f"Allowed: {[str(p) for p in self.allowed_paths]}"
                )
            
            return path
        
        except Exception as e:
            if isinstance(e, SecurityError):
                raise
            raise SecurityError(f"Invalid path '{path_str}': {str(e)}")
    
    def add_allowed_path(self, path_str: str):
        """Add an additional allowed path for filesystem operations"""
        path = Path(path_str).resolve()
        if path not in self.allowed_paths:
            self.allowed_paths.append(path)
            logger.info(f"Added allowed path: {path}")
    
    async def read_file(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Read contents of a file
        
        Args:
            path: Path to the file to read
            encoding: File encoding (default: utf-8)
            
        Returns:
            Dict with file content and metadata
        """
        try:
            file_path = self._validate_path(path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File does not exist: {path}",
                    "content": ""
                }
            
            if not file_path.is_file():
                return {
                    "success": False,
                    "error": f"Path is not a file: {path}",
                    "content": ""
                }
            
            # Try to detect if file is binary
            try:
                with open(file_path, 'rb') as f:
                    chunk = f.read(1024)
                    if b'\x00' in chunk:
                        # File contains null bytes, likely binary
                        return {
                            "success": False,
                            "error": f"Cannot read binary file as text: {path}",
                            "content": "",
                            "is_binary": True
                        }
            except Exception:
                pass
            
            # Read text file
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            file_size = file_path.stat().st_size
            modified_time = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            
            logger.info(f"Read file: {path} ({file_size} bytes)")
            
            return {
                "success": True,
                "content": content,
                "size": file_size,
                "modified": modified_time,
                "path": str(file_path)
            }
        
        except SecurityError as e:
            logger.warning(f"Security violation in read_file: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
        
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return {
                "success": False,
                "error": f"Failed to read file: {str(e)}",
                "content": ""
            }
    
    async def write_file(self, path: str, content: str, 
                        encoding: str = "utf-8", create_dirs: bool = True) -> Dict[str, Any]:
        """
        Write content to a file
        
        Args:
            path: Path to the file to write
            content: Content to write
            encoding: File encoding (default: utf-8)
            create_dirs: Create parent directories if they don't exist
            
        Returns:
            Dict with operation result and metadata
        """
        try:
            file_path = self._validate_path(path)
            
            # Create parent directories if needed
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            file_size = file_path.stat().st_size
            modified_time = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            
            logger.info(f"Wrote file: {path} ({file_size} bytes)")
            
            return {
                "success": True,
                "message": f"Successfully wrote {file_size} bytes to {path}",
                "size": file_size,
                "modified": modified_time,
                "path": str(file_path)
            }
        
        except SecurityError as e:
            logger.warning(f"Security violation in write_file: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
        except Exception as e:
            logger.error(f"Error writing file {path}: {e}")
            return {
                "success": False,
                "error": f"Failed to write file: {str(e)}"
            }
    
    async def list_directory(self, path: str = ".", 
                           show_hidden: bool = False) -> Dict[str, Any]:
        """
        List contents of a directory
        
        Args:
            path: Path to the directory to list
            show_hidden: Include hidden files and directories
            
        Returns:
            Dict with directory listing and metadata
        """
        try:
            dir_path = self._validate_path(path)
            
            if not dir_path.exists():
                return {
                    "success": False,
                    "error": f"Directory does not exist: {path}",
                    "entries": []
                }
            
            if not dir_path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {path}",
                    "entries": []
                }
            
            entries = []
            
            for item in dir_path.iterdir():
                # Skip hidden files if not requested
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                try:
                    stat_info = item.stat()
                    
                    entry = {
                        "name": item.name,
                        "path": str(item.relative_to(self.shared_dir)),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat_info.st_size if item.is_file() else None,
                        "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        "permissions": oct(stat_info.st_mode)[-3:],
                        "is_symlink": item.is_symlink()
                    }
                    
                    entries.append(entry)
                
                except Exception as e:
                    # Skip items that can't be accessed
                    logger.debug(f"Skipping inaccessible item {item}: {e}")
                    continue
            
            # Sort entries: directories first, then by name
            entries.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
            
            logger.info(f"Listed directory: {path} ({len(entries)} entries)")
            
            return {
                "success": True,
                "entries": entries,
                "path": str(dir_path),
                "total_count": len(entries)
            }
        
        except SecurityError as e:
            logger.warning(f"Security violation in list_directory: {e}")
            return {
                "success": False,
                "error": str(e),
                "entries": []
            }
        
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return {
                "success": False,
                "error": f"Failed to list directory: {str(e)}",
                "entries": []
            }
    
    async def create_directory(self, path: str, 
                             parents: bool = True) -> Dict[str, Any]:
        """
        Create a new directory
        
        Args:
            path: Path to the directory to create
            parents: Create parent directories if they don't exist
            
        Returns:
            Dict with operation result
        """
        try:
            dir_path = self._validate_path(path)
            
            if dir_path.exists():
                if dir_path.is_dir():
                    return {
                        "success": True,
                        "message": f"Directory already exists: {path}",
                        "path": str(dir_path)
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Path exists but is not a directory: {path}"
                    }
            
            dir_path.mkdir(parents=parents, exist_ok=True)
            
            logger.info(f"Created directory: {path}")
            
            return {
                "success": True,
                "message": f"Successfully created directory: {path}",
                "path": str(dir_path)
            }
        
        except SecurityError as e:
            logger.warning(f"Security violation in create_directory: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
        except Exception as e:
            logger.error(f"Error creating directory {path}: {e}")
            return {
                "success": False,
                "error": f"Failed to create directory: {str(e)}"
            }
    
    async def delete_file(self, path: str) -> Dict[str, Any]:
        """
        Delete a file
        
        Args:
            path: Path to the file to delete
            
        Returns:
            Dict with operation result
        """
        try:
            file_path = self._validate_path(path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File does not exist: {path}"
                }
            
            if file_path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is a directory, not a file: {path}. Use delete_directory instead."
                }
            
            file_path.unlink()
            
            logger.info(f"Deleted file: {path}")
            
            return {
                "success": True,
                "message": f"Successfully deleted file: {path}",
                "path": str(file_path)
            }
        
        except SecurityError as e:
            logger.warning(f"Security violation in delete_file: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
        except Exception as e:
            logger.error(f"Error deleting file {path}: {e}")
            return {
                "success": False,
                "error": f"Failed to delete file: {str(e)}"
            }
    
    async def move_file(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Move or rename a file
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            Dict with operation result
        """
        try:
            source_path = self._validate_path(source)
            dest_path = self._validate_path(destination)
            
            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"Source file does not exist: {source}"
                }
            
            if dest_path.exists():
                return {
                    "success": False,
                    "error": f"Destination already exists: {destination}"
                }
            
            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(source_path), str(dest_path))
            
            logger.info(f"Moved file: {source} -> {destination}")
            
            return {
                "success": True,
                "message": f"Successfully moved file from {source} to {destination}",
                "source": str(source_path),
                "destination": str(dest_path)
            }
        
        except SecurityError as e:
            logger.warning(f"Security violation in move_file: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
        except Exception as e:
            logger.error(f"Error moving file {source} to {destination}: {e}")
            return {
                "success": False,
                "error": f"Failed to move file: {str(e)}"
            }
    
    async def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        Get information about a file or directory
        
        Args:
            path: Path to the file or directory
            
        Returns:
            Dict with file information
        """
        try:
            file_path = self._validate_path(path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"Path does not exist: {path}"
                }
            
            stat_info = file_path.stat()
            
            info = {
                "success": True,
                "name": file_path.name,
                "path": str(file_path),
                "relative_path": str(file_path.relative_to(self.shared_dir)),
                "type": "directory" if file_path.is_dir() else "file",
                "size": stat_info.st_size,
                "created": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                "permissions": oct(stat_info.st_mode)[-3:],
                "is_symlink": file_path.is_symlink(),
                "is_readable": os.access(file_path, os.R_OK),
                "is_writable": os.access(file_path, os.W_OK),
                "is_executable": os.access(file_path, os.X_OK)
            }
            
            if file_path.is_file():
                # Additional file-specific information
                try:
                    with open(file_path, 'rb') as f:
                        chunk = f.read(1024)
                        info["is_binary"] = b'\x00' in chunk
                        info["is_empty"] = len(chunk) == 0
                except Exception:
                    info["is_binary"] = None
                    info["is_empty"] = None
            
            logger.debug(f"Retrieved file info: {path}")
            
            return info
        
        except SecurityError as e:
            logger.warning(f"Security violation in get_file_info: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
        except Exception as e:
            logger.error(f"Error getting file info {path}: {e}")
            return {
                "success": False,
                "error": f"Failed to get file info: {str(e)}"
            }
    
    async def search_files(self, directory: str, pattern: str, 
                          recursive: bool = True) -> Dict[str, Any]:
        """
        Search for files matching a pattern
        
        Args:
            directory: Directory to search in
            pattern: Search pattern (glob-style)
            recursive: Search recursively in subdirectories
            
        Returns:
            Dict with search results
        """
        try:
            search_dir = self._validate_path(directory)
            
            if not search_dir.exists():
                return {
                    "success": False,
                    "error": f"Directory does not exist: {directory}",
                    "matches": []
                }
            
            if not search_dir.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {directory}",
                    "matches": []
                }
            
            matches = []
            
            if recursive:
                # Use ** for recursive globbing
                search_pattern = f"**/{pattern}"
                glob_pattern = search_dir / search_pattern
                matched_paths = glob.glob(str(glob_pattern), recursive=True)
            else:
                glob_pattern = search_dir / pattern
                matched_paths = glob.glob(str(glob_pattern))
            
            for match_path in matched_paths:
                try:
                    path_obj = Path(match_path)
                    
                    # Ensure match is within allowed paths
                    self._validate_path(str(path_obj))
                    
                    stat_info = path_obj.stat()
                    
                    match_info = {
                        "name": path_obj.name,
                        "path": str(path_obj),
                        "relative_path": str(path_obj.relative_to(self.shared_dir)),
                        "type": "directory" if path_obj.is_dir() else "file",
                        "size": stat_info.st_size if path_obj.is_file() else None,
                        "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                    }
                    
                    matches.append(match_info)
                
                except Exception as e:
                    logger.debug(f"Skipping match {match_path}: {e}")
                    continue
            
            # Sort matches by path
            matches.sort(key=lambda x: x["path"])
            
            logger.info(f"Search completed: {directory} / {pattern} ({len(matches)} matches)")
            
            return {
                "success": True,
                "matches": matches,
                "total_count": len(matches),
                "search_directory": str(search_dir),
                "pattern": pattern,
                "recursive": recursive
            }
        
        except SecurityError as e:
            logger.warning(f"Security violation in search_files: {e}")
            return {
                "success": False,
                "error": str(e),
                "matches": []
            }
        
        except Exception as e:
            logger.error(f"Error searching files in {directory} with pattern {pattern}: {e}")
            return {
                "success": False,
                "error": f"Failed to search files: {str(e)}",
                "matches": []
            }
    
    async def copy_file(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Copy a file to a new location
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            Dict with operation result
        """
        try:
            source_path = self._validate_path(source)
            dest_path = self._validate_path(destination)
            
            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"Source file does not exist: {source}"
                }
            
            if not source_path.is_file():
                return {
                    "success": False,
                    "error": f"Source is not a file: {source}"
                }
            
            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(str(source_path), str(dest_path))
            
            dest_size = dest_path.stat().st_size
            
            logger.info(f"Copied file: {source} -> {destination} ({dest_size} bytes)")
            
            return {
                "success": True,
                "message": f"Successfully copied file from {source} to {destination}",
                "source": str(source_path),
                "destination": str(dest_path),
                "size": dest_size
            }
        
        except SecurityError as e:
            logger.warning(f"Security violation in copy_file: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
        except Exception as e:
            logger.error(f"Error copying file {source} to {destination}: {e}")
            return {
                "success": False,
                "error": f"Failed to copy file: {str(e)}"
            }