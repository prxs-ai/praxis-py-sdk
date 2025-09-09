#!/usr/bin/env python3

import sys
import json
import os
import platform
import psutil
import socket
from datetime import datetime
from pathlib import Path


def get_system_info() -> dict:
    try:
        info = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "system": {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "hostname": socket.gethostname()
            },
            "resources": {},
            "network": {},
            "environment": {},
            "filesystem": {}
        }
        
        try:
            info["resources"]["cpu_count"] = psutil.cpu_count()
            info["resources"]["cpu_count_logical"] = psutil.cpu_count(logical=True)
            info["resources"]["cpu_percent"] = psutil.cpu_percent(interval=1)
            info["resources"]["load_average"] = os.getloadavg() if hasattr(os, 'getloadavg') else "N/A"
        except Exception as e:
            info["resources"]["error"] = f"CPU info error: {str(e)}"
        
        try:
            memory = psutil.virtual_memory()
            info["resources"]["memory"] = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free
            }
        except Exception as e:
            info["resources"]["memory_error"] = str(e)
        
        try:
            disk = psutil.disk_usage('/')
            info["filesystem"]["root_disk"] = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            }
        except Exception as e:
            info["filesystem"]["disk_error"] = str(e)
        
        try:
            info["filesystem"]["current_working_directory"] = str(Path.cwd())
            info["filesystem"]["temp_directory"] = os.environ.get('TMPDIR', '/tmp')
        except Exception as e:
            info["filesystem"]["path_error"] = str(e)
        
        try:
            info["network"]["local_ip"] = socket.gethostbyname(socket.gethostname())
        except Exception as e:
            info["network"]["ip_error"] = str(e)
        
        try:
            important_env_vars = [
                'PATH', 'HOME', 'USER', 'SHELL', 'LANG', 'TZ', 
                'TMPDIR', 'PYTHONPATH', 'VIRTUAL_ENV'
            ]
            info["environment"]["selected_vars"] = {
                var: os.environ.get(var, "Not set") for var in important_env_vars
            }
            info["environment"]["total_env_vars"] = len(os.environ)
        except Exception as e:
            info["environment"]["env_error"] = str(e)
        
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            info["system"]["boot_time"] = boot_time.isoformat()
            info["system"]["uptime_seconds"] = (datetime.now() - boot_time).total_seconds()
        except Exception as e:
            info["system"]["boot_time_error"] = str(e)
        
        return info
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


def main():
    detailed = os.environ.get('DETAILED') or os.environ.get('detailed')
    format_type = os.environ.get('FORMAT') or os.environ.get('format') or 'json'
    
    result = get_system_info()
    
    if detailed and detailed.lower() in ['false', '0', 'no']:
        if result.get("success"):
            simplified = {
                "success": True,
                "platform": result["system"]["platform"],
                "hostname": result["system"]["hostname"],
                "python_version": result["system"]["python_version"],
                "cpu_count": result["resources"].get("cpu_count"),
                "memory_total_gb": round(result["resources"]["memory"]["total"] / (1024**3), 2) if "memory" in result["resources"] else "N/A",
                "timestamp": result["timestamp"]
            }
            result = simplified
    
    if format_type.lower() == 'compact':
        print(json.dumps(result, separators=(',', ':')))
    else:
        print(json.dumps(result, indent=2))
    
    if not result.get("success", False):
        sys.exit(1)


if __name__ == "__main__":
    main()