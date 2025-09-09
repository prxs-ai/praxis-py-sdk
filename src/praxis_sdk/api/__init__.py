"""
Praxis SDK API Module

Comprehensive FastAPI-based API gateway for Praxis Python SDK with:
- HTTP REST endpoints for agent interaction
- WebSocket real-time event streaming
- A2A protocol support
- P2P tool invocation
- Task management
- Trio-asyncio integration
"""

from .gateway import APIGateway, api_gateway, app
from .handlers import RequestHandlers, request_handlers
from .websocket import WebSocketManager, websocket_manager, WebSocketConnection, MessageType
from .server import PraxisAPIServer, server
from .models import (
    APIResponse, APIError, ToolInfo, HealthResponse, TaskResponse, TaskListResponse,
    ExecuteDSLRequest, ExecuteDSLResponse, ToolInvokeRequest, ToolInvokeResponse,
    WebSocketMessage, WebSocketEvent, build_error_response, RequestValidator
)

__all__ = [
    # Main API Gateway
    "APIGateway",
    "api_gateway",
    "app",
    
    # Request Handlers
    "RequestHandlers", 
    "request_handlers",
    
    # WebSocket Manager
    "WebSocketManager",
    "websocket_manager",
    "WebSocketConnection",
    "MessageType",
    
    # Server
    "PraxisAPIServer",
    "server",
    
    # Models
    "APIResponse",
    "APIError", 
    "ToolInfo",
    "HealthResponse",
    "TaskResponse",
    "TaskListResponse",
    "ExecuteDSLRequest",
    "ExecuteDSLResponse",
    "ToolInvokeRequest",
    "ToolInvokeResponse",
    "WebSocketMessage",
    "WebSocketEvent",
    "build_error_response",
    "RequestValidator",
]