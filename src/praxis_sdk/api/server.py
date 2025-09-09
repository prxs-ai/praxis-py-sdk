"""
FastAPI Server Integration for Praxis Python SDK.

Provides a complete ASGI server implementation that integrates all components:
- FastAPI application with CORS and middleware
- WebSocket connection handling
- Trio-asyncio event loop integration
- Background task management
- Health monitoring
- Graceful shutdown handling
"""

import signal
import asyncio
import socket
import sys
from contextlib import asynccontextmanager
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import trio
import trio_asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, BackgroundTasks, Depends, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from praxis_sdk.a2a.models import (
    A2AAgentCard, Task, Message, create_praxis_skills, 
    create_default_capabilities, A2AProvider, create_dynamic_agent_card,
    JSONRPCRequest
)
from praxis_sdk.api.gateway import api_gateway, ToolInfo
from praxis_sdk.api.handlers import initialize_request_handlers, get_request_handlers
from praxis_sdk.api.websocket import websocket_manager, WebSocketConnection
from praxis_sdk.api.workflow_handlers import workflow_handlers, WorkflowExecutionPayload, WorkflowCancelRequest
from praxis_sdk.api.static_server import static_file_handlers
from praxis_sdk.bus import event_bus, EventType
from praxis_sdk.config import load_config


class PraxisAPIServer:
    """
    Complete FastAPI server for Praxis SDK with integrated components.
    
    Features:
    - FastAPI application with custom middleware
    - WebSocket connection management
    - Event bus integration
    - Trio-asyncio async context management
    - Health monitoring and statistics
    - Graceful shutdown handling
    """
    
    def __init__(self):
        self.config = load_config()
        self.app = self._create_app()
        self._running = False
        self._nursery: Optional[trio.Nursery] = None
        self._agent = None  # Will be attached by PraxisAgent
        
        # Initialize request handlers without agent first (for basic functionality)
        initialize_request_handlers(agent=None)
        
        # Initialize components in proper order
        self._setup_tools()
        self._setup_agent_card()

    # Context from running agent (p2p, bus)
    def attach_context(self, agent, event_bus_obj=None):
        """Attach running agent context for P2P operations and shared bus."""
        self._agent = agent
        
        # Re-initialize request handlers with agent reference for DSL orchestration
        initialize_request_handlers(agent=agent)
        logger.info("Request handlers re-initialized with agent reference for LLM orchestration")
        
        if event_bus_obj is not None:
            # Optionally align server with agent's bus instance
            global event_bus
            event_bus = event_bus_obj
        logger.info("API server attached to running agent context")

        # Ensure Agent Card is re-applied to API gateway and handlers after re-init
        try:
            # Use agent’s A2A card for HTTP publication
            card_dict = agent.get_agent_card()  # dict with aliases
            from praxis_sdk.a2a.models import A2AAgentCard
            agent_card = A2AAgentCard(**card_dict)

            # Compatibility fields for HTTP publication
            agent_card.version = agent_card.version or "1.0.0"
            agent_card.supported_transports = ["http"]

            api_gateway.set_agent_card(agent_card)
            get_request_handlers().set_agent_card(agent_card)
            logger.info("Agent card re-applied to API handlers after context attach")
        except Exception as e:
            logger.warning(f"Failed to apply agent card on attach: {e}")
    
    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan handler."""
            # Startup
            logger.info("Starting Praxis API server...")
            await self._startup()
            
            yield
            
            # Shutdown
            logger.info("Shutting down Praxis API server...")
            await self._shutdown()
        
        app = FastAPI(
            title="Praxis Agent API",
            description="REST and WebSocket API for Praxis Python SDK",
            version="1.0.0",
            docs_url="/docs" if self.config.api.docs_enabled else None,
            redoc_url="/redoc" if self.config.api.docs_enabled else None,
            lifespan=lifespan
        )
        
        # Add middleware
        self._setup_middleware(app)
        
        # Add routes
        self._setup_routes(app)
        
        # Add exception handlers
        self._setup_exception_handlers(app)
        
        return app
    
    def _setup_middleware(self, app: FastAPI):
        """Setup FastAPI middleware."""
        
        # CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.api.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Trusted host middleware (for production)
        if self.config.environment == "production":
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"]
            )
        
        # Custom request logging middleware
        @app.middleware("http")
        async def log_requests(request, call_next):
            start_time = trio.current_time()
            response = await call_next(request)
            process_time = trio.current_time() - start_time
            
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.3f}s"
            )
            return response
    
    def _setup_routes(self, app: FastAPI):
        """Setup API routes."""
        
        # Health endpoint
        @app.get("/health")
        async def health_check():
            return await get_request_handlers().handle_health_check()
        
        # Agent card endpoint
        @app.get("/agent/card", response_model=A2AAgentCard)
        async def get_agent_card():
            return await get_request_handlers().handle_get_agent_card()
        
        # Main execution endpoint (A2A standard)
        @app.post("/execute")
        async def execute_command_a2a(request: dict, background_tasks: BackgroundTasks):
            """Main A2A execution endpoint supporting JSON-RPC 2.0"""
            return await get_request_handlers().handle_execute_command(request, background_tasks)
        
        # Legacy command execution endpoint
        @app.post("/agent/execute") 
        async def execute_command_legacy(request: dict, background_tasks: BackgroundTasks):
            """Legacy execution endpoint for backward compatibility"""
            return await get_request_handlers().handle_execute_command(request, background_tasks)
        
        # Task management endpoints
        @app.get("/tasks/{task_id}", response_model=Task)
        async def get_task(task_id: str):
            return await get_request_handlers().handle_get_task(task_id)
        
        @app.get("/tasks")
        async def list_tasks(
            state: Optional[str] = None,
            limit: int = 100,
            offset: int = 0
        ):
            from praxis_sdk.a2a.models import TaskState
            task_state = TaskState(state) if state else None
            return await get_request_handlers().handle_list_tasks(task_state, limit, offset)
        
        @app.post("/tasks", response_model=Task)
        async def create_task(message: Message, background_tasks: BackgroundTasks):
            return await get_request_handlers().handle_create_task(message, background_tasks)
        
        # Tool management endpoints
        @app.get("/tools")
        async def list_tools():
            return await get_request_handlers().handle_list_tools()
        
        @app.post("/tools/{tool_name}/invoke")
        async def invoke_tool(
            tool_name: str,
            request: dict,
            background_tasks: BackgroundTasks
        ):
            parameters = request.get("parameters", {})
            context_id = request.get("context_id")
            return await get_request_handlers().handle_invoke_tool(
                tool_name, parameters, context_id, background_tasks
            )
        
        # P2P endpoints
        @app.get("/p2p/info")
        async def p2p_info():
            """Return local peer_id and suggested multiaddrs.

            This does not depend on the running P2PService; it derives peer_id
            from the local keystore seed if present.
            """
            import os
            from libp2p.crypto.ed25519 import create_new_key_pair
            from libp2p.peer.id import ID as PeerID

            # Attempt to read seed from configured keystore
            keystore_dir = self.config.p2p.keystore_path
            seed_path = os.path.join(keystore_dir, "node.key")
            peer_id = None
            try:
                if os.path.exists(seed_path):
                    with open(seed_path, "rb") as f:
                        seed = f.read()
                    kp = create_new_key_pair(seed)
                    pid = PeerID.from_pubkey(kp.public_key)
                    peer_id = pid.to_base58()
            except Exception as e:
                logger.warning(f"Failed to derive peer id from seed: {e}")

            hostname = socket.gethostname()
            port = self.config.p2p.port
            addrs = []
            if peer_id:
                addrs = [
                    f"/dns4/{hostname}/tcp/{port}/p2p/{peer_id}",
                    f"/ip4/0.0.0.0/tcp/{port}/p2p/{peer_id}",
                ]

            return {
                "peer_id": peer_id,
                "listen_port": port,
                "suggested_multiaddrs": addrs,
            }

        @app.get("/p2p/cards")
        async def list_peer_cards():
            if not self._agent or not self._agent.p2p_service:
                return {"cards": {}, "count": 0}
            cards = self._agent.p2p_service.peer_cards
            return {"cards": cards, "count": len(cards)}

        @app.get("/p2p/tools")
        async def list_peer_tools():
            """List visible tools from connected peers (for debugging)."""
            if not self._agent or not self._agent.p2p_service:
                return {"tools": {}, "count": 0}
            tools_map = self._agent.p2p_service.get_all_peer_tools()
            # Convert peer_id keys to peer names when available for readability
            pretty = {}
            for peer_id, tools in tools_map.items():
                name = self._agent.p2p_service.peer_cards.get(peer_id, {}).get("name", peer_id)
                pretty[f"{name} ({peer_id[:8]}...)"] = tools
            return {"tools": pretty, "count": len(tools_map)}

        @app.post("/p2p/connect")
        async def p2p_connect(request: Dict[str, Any]):
            if not self._agent or not self._agent.p2p_service:
                return JSONResponse(status_code=503, content={"error": "P2P service not available"})
            addr = request.get("multiaddr") or request.get("addr")
            if not addr:
                return JSONResponse(status_code=400, content={"error": "multiaddr is required"})
            try:
                result = await self._agent.p2p_service.connect_to_peer(addr)
                return result
            except Exception as e:
                return JSONResponse(status_code=500, content={"error": str(e)})

        @app.post("/p2p/a2a")
        async def p2p_a2a(payload: Dict[str, Any]):
            """Send a raw A2A JSON-RPC request to a peer over libp2p.

            Body: {"peer_id": "<peerId>", "request": {"jsonrpc":"2.0","id":...,"method":"...","params":{...}}}
            """
            if not self._agent or not self._agent.p2p_service:
                return JSONResponse(status_code=503, content={"error": "P2P service not available"})
            peer_id = payload.get("peer_id")
            req = payload.get("request")
            if not peer_id or not isinstance(req, dict):
                return JSONResponse(status_code=400, content={"error": "peer_id and request are required"})
            try:
                result = await self._agent.p2p_service.send_a2a_request(peer_id, req)
                return result
            except Exception as e:
                return JSONResponse(status_code=500, content={"error": str(e)})

        @app.post("/p2p/tool")
        async def invoke_p2p_tool(payload: Dict[str, Any]):
            """New P2P tool invocation endpoint (replaces /p2p/tools/{peer_id}/invoke)"""
            if not self._agent or not self._agent.p2p_service:
                return JSONResponse(status_code=503, content={"error": "P2P service not available"})
            
            peer_id = payload.get("peer_id")
            tool = payload.get("tool") or payload.get("name")
            args = payload.get("arguments", {})
            
            if not peer_id:
                return JSONResponse(status_code=400, content={"error": "peer_id is required"})
            if not tool:
                return JSONResponse(status_code=400, content={"error": "tool is required"})
            
            try:
                result = await self._agent.p2p_service.invoke_remote_tool(peer_id, tool, args)
                return result
            except Exception as e:
                return JSONResponse(status_code=500, content={"error": str(e)})
        
        # Legacy P2P tool endpoint (for backward compatibility)
        @app.post("/p2p/tools/{peer_id}/invoke")
        async def invoke_remote_tool_legacy(peer_id: str, payload: Dict[str, Any]):
            """Legacy P2P tool invocation endpoint (deprecated, use /p2p/tool)"""
            if not self._agent or not self._agent.p2p_service:
                return JSONResponse(status_code=503, content={"error": "P2P service not available"})
            tool = payload.get("tool") or payload.get("name")
            args = payload.get("arguments", {})
            if not tool:
                return JSONResponse(status_code=400, content={"error": "tool is required"})
            try:
                result = await self._agent.p2p_service.invoke_remote_tool(peer_id, tool, args)
                return result
            except Exception as e:
                return JSONResponse(status_code=500, content={"error": str(e)})
        @app.get("/p2p/peers")
        async def list_p2p_peers():
            if not self._agent or not self._agent.p2p_service:
                return {"peers": [], "count": 0}
            peers = self._agent.p2p_service.get_connected_peers()
            return {"peers": peers, "count": len(peers)}
        
        @app.get("/peers")
        async def get_discovered_peers():
            """Get all discovered peers and local peer info"""
            result = {
                "local_peer_id": None,
                "peers": [],
                "count": 0
            }
            
            # Get local peer ID
            if self._agent and hasattr(self._agent, 'p2p_service') and self._agent.p2p_service:
                try:
                    local_peer_id = self._agent.p2p_service.get_peer_id()
                    result["local_peer_id"] = local_peer_id
                    
                    # Get connected peers from P2P service
                    connected_peers = self._agent.p2p_service.get_connected_peers()
                    result["peers"] = connected_peers
                    result["count"] = len(connected_peers)
                except Exception as e:
                    logger.debug(f"Could not get P2P info: {e}")
            
            # Fallback to mDNS discovery if available
            if not result["peers"] and self._agent and hasattr(self._agent, 'p2p_discovery') and self._agent.p2p_discovery:
                try:
                    peers = await self._agent.p2p_discovery.get_peers()
                    result["peers"] = peers
                    result["count"] = len(peers)
                except Exception as e:
                    logger.error(f"Error getting discovered peers: {e}")
            
            return result
        
        @app.get("/card")
        async def get_agent_card_simple():
            """Get the agent card (simplified endpoint)"""
            return await get_request_handlers().handle_get_agent_card()
        
        # Test endpoint for cross-agent communication validation
        @app.get("/api/test/query-peer-card")
        async def test_query_peer_card(peer_url: str):
            """Test endpoint to query another agent's card for cross-agent communication testing"""
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{peer_url}/agent/card", timeout=5) as response:
                        if response.status == 200:
                            card_data = await response.json()
                            return {
                                "success": True,
                                "card": card_data,
                                "peer_url": peer_url,
                                "status_code": response.status
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"HTTP {response.status}",
                                "peer_url": peer_url
                            }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "peer_url": peer_url
                }
        
        @app.get("/.well-known/agent-card.json", response_model=A2AAgentCard)
        async def get_well_known_agent_card():
            """Get the agent card at A2A standard location"""
            return await get_request_handlers().handle_get_agent_card()
        
        # Statistics endpoint
        @app.get("/stats")
        async def get_statistics():
            return {
                "api_gateway": api_gateway.get_stats(),
                "get_request_handlers()": get_request_handlers().get_stats(),
                "websocket_manager": websocket_manager.get_stats(),
                "event_bus": event_bus.get_stats(),
                "server": {
                    "running": self._running,
                    "config": {
                        "environment": self.config.environment,
                        "api_host": self.config.api.host,
                        "api_port": self.config.api.port,
                        "websocket_enabled": self.config.api.websocket_enabled,
                        "p2p_enabled": self.config.p2p.enabled,
                    }
                }
            }
        
        # A2A Direct Endpoints (for full A2A protocol compliance)
        @app.post("/a2a/message/send")
        async def a2a_message_send(request: dict, background_tasks: BackgroundTasks):
            """Direct A2A message/send endpoint - handles JSON-RPC 2.0 format only"""
            try:
                # Ensure this is a proper JSON-RPC request
                jsonrpc_request = JSONRPCRequest(**request)
                if jsonrpc_request.method != "message/send":
                    return JSONResponse(
                        status_code=400, 
                        content={"error": "Invalid method for this endpoint"}
                    )
                return await get_request_handlers()._handle_message_send(jsonrpc_request, background_tasks)
            except Exception as e:
                logger.error(f"Error in A2A message/send endpoint: {e}")
                return JSONResponse(status_code=400, content={"error": str(e)})
        
        @app.post("/a2a/tasks/get")
        async def a2a_tasks_get(request: dict):
            """Direct A2A tasks/get endpoint - handles JSON-RPC 2.0 format only"""
            try:
                # Ensure this is a proper JSON-RPC request
                jsonrpc_request = JSONRPCRequest(**request)
                if jsonrpc_request.method != "tasks/get":
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid method for this endpoint"}
                    )
                return await get_request_handlers()._handle_tasks_get(jsonrpc_request)
            except Exception as e:
                logger.error(f"Error in A2A tasks/get endpoint: {e}")
                return JSONResponse(status_code=400, content={"error": str(e)})

        @app.get("/a2a/tasks/stream/{task_id}")
        async def a2a_tasks_stream(task_id: str, request: Request):
            """SSE stream for task updates as JSON-RPC responses (spec 3.3 JSON-RPC Streaming).

            Emits one JSON-RPC 2.0 Response per SSE `data:` frame with latest task snapshot.
            """
            handlers = get_request_handlers()

            async def event_generator():
                last_sent = None
                stream_id = f"tasks/stream:{task_id}"
                while True:
                    # Client disconnect
                    if await request.is_disconnected():
                        logger.info(f"A2A SSE disconnect for task {task_id}")
                        break
                    try:
                        task = handlers.tasks.get(task_id)
                        if task is not None:
                            snapshot = task.dict()
                            # send only on change
                            if snapshot != last_sent:
                                last_sent = snapshot
                                payload = {
                                    "jsonrpc": "2.0",
                                    "id": stream_id,
                                    "result": {
                                        "event": "task.update",
                                        "task": snapshot
                                    }
                                }
                                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    except Exception as e:
                        err = {
                            "jsonrpc": "2.0",
                            "id": stream_id,
                            "error": {"code": -32000, "message": str(e)}
                        }
                        yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"
                    # Throttle
                    await asyncio.sleep(1)

            headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
            return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)

        @app.get("/a2a/message/stream")
        async def a2a_message_stream(task_id: Optional[str] = None, request: Request = None):
            """Alias stream for message/stream: emits DSL and task progress for a given task id (if provided)."""
            handlers = get_request_handlers()

            async def event_generator():
                last_sent = {"progress": 0}
                stream_id = f"message/stream:{task_id or 'all'}"
                while True:
                    if await request.is_disconnected():
                        logger.info(f"A2A SSE message stream disconnect (task_id={task_id})")
                        break
                    try:
                        payload: Dict[str, Any] = {"event": "heartbeat", "ts": datetime.utcnow().isoformat() + "Z"}
                        if task_id:
                            task = handlers.tasks.get(task_id)
                            if task is not None:
                                payload = {"event": "message.progress", "task": task.dict()}
                        frame = {"jsonrpc": "2.0", "id": stream_id, "result": payload}
                        yield f"data: {json.dumps(frame, ensure_ascii=False)}\n\n"
                    except Exception as e:
                        err = {"jsonrpc": "2.0", "id": stream_id, "error": {"code": -32000, "message": str(e)}}
                        yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(2)

            headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
            return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)
        
        @app.get("/a2a/tasks")
        async def a2a_tasks_list(
            state: Optional[str] = None,
            limit: int = 100,
            offset: int = 0
        ):
            """Direct A2A tasks list endpoint - returns tasks in A2A format"""
            try:
                from praxis_sdk.a2a.models import TaskState
                task_state = TaskState(state) if state else None
                
                # Get tasks using existing handler
                result = await get_request_handlers().handle_list_tasks(task_state, limit, offset)
                
                # Convert to A2A format (already compatible)
                return result
            except Exception as e:
                logger.error(f"Error in A2A tasks list endpoint: {e}")
                return JSONResponse(status_code=500, content={"error": str(e)})
        
        # MCP endpoints
        @app.get("/mcp/tools")
        async def get_mcp_tools():
            """Get all available MCP tools (Go compatibility format)"""
            try:
                from praxis_sdk.mcp.service import mcp_service
                tools = mcp_service.get_tools()
                
                # Convert to Go-compatible format
                return {
                    "tools": tools,
                    "count": len(tools),
                    "agent": self.config.agents[0].name if self.config.agents else "Praxis Agent"
                }
            except Exception as e:
                logger.error(f"Error getting MCP tools: {e}")
                return JSONResponse(status_code=500, content={"error": str(e)})
        
        @app.get("/mcp/tools/schemas")
        async def get_mcp_tool_schemas():
            """Get JSON schemas for all MCP tools"""
            try:
                from praxis_sdk.mcp.service import mcp_service
                schemas = mcp_service.get_tool_schemas()
                
                return {
                    "schemas": schemas,
                    "total": len(schemas),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            except Exception as e:
                logger.error(f"Error getting MCP tool schemas: {e}")
                return JSONResponse(status_code=500, content={"error": str(e)})
        
        @app.get("/mcp/stats")
        async def get_mcp_statistics():
            """Get MCP service statistics"""
            try:
                from praxis_sdk.mcp.service import mcp_service
                stats = mcp_service.get_statistics()
                return stats
            except Exception as e:
                logger.error(f"Error getting MCP statistics: {e}")
                return JSONResponse(status_code=500, content={"error": str(e)})
        
        # Cache endpoints
        @app.get("/cache/stats")
        async def get_cache_stats():
            """Get cache statistics (Go compatibility format)"""
            try:
                from praxis_sdk.cache.service import cache_service
                stats = cache_service.get_stats()
                
                # Convert to Go-compatible format (cache.size and enabled fields)
                cache_info = stats.get("cache_info", {})
                return {
                    "cache": {
                        "size": cache_info.get("total_items", 0),
                        "enabled": True
                    },
                    "agent": self.config.agents[0].name if self.config.agents else "Praxis Agent"
                }
            except Exception as e:
                logger.error(f"Error getting cache statistics: {e}")
                return JSONResponse(status_code=500, content={"error": str(e)})
        
        @app.delete("/cache")
        async def clear_cache():
            """Clear cache entries (Go compatibility format)"""
            try:
                from praxis_sdk.cache.service import cache_service
                result = cache_service.clear()
                
                # Return Go-compatible format
                return {
                    "status": "cache cleared",
                    "agent": self.config.agents[0].name if self.config.agents else "Praxis Agent"
                }
            except Exception as e:
                logger.error(f"Error clearing cache: {e}")
                return JSONResponse(status_code=500, content={"error": str(e)})
        
        @app.get("/cache/cleanup")
        async def cleanup_expired_cache():
            """Clean up expired cache entries"""
            try:
                from praxis_sdk.cache.service import cache_service
                removed_count = cache_service.cleanup_expired()
                
                return {
                    "success": True,
                    "removed_count": removed_count,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            except Exception as e:
                logger.error(f"Error cleaning up cache: {e}")
                return JSONResponse(status_code=500, content={"error": str(e)})
        
        # ========== WORKFLOW API ENDPOINTS (Frontend Integration) ==========
        
        # Main workflow endpoints expected by React frontend
        @app.post("/api/workflow/execute")
        async def execute_workflow_endpoint(payload: WorkflowExecutionPayload, background_tasks: BackgroundTasks):
            """Execute workflow - CRITICAL frontend endpoint"""
            return await workflow_handlers.execute_workflow(payload, background_tasks)
        
        @app.post("/api/workflow/cancel/{workflow_id}")
        async def cancel_workflow_endpoint(workflow_id: str, request: WorkflowCancelRequest):
            """Cancel workflow execution"""
            return await workflow_handlers.cancel_workflow(workflow_id, request)
        
        @app.get("/api/workflow/status/{workflow_id}")
        async def get_workflow_status_endpoint(workflow_id: str):
            """Get workflow status - CRITICAL frontend endpoint"""
            return await workflow_handlers.get_workflow_status(workflow_id)
        
        @app.get("/api/workflow/list")
        async def list_workflows_endpoint(
            state: Optional[str] = None,
            limit: int = 100,
            offset: int = 0
        ):
            """List all workflows with pagination"""
            return await workflow_handlers.list_workflows(state, limit, offset)
        
        @app.get("/api/workflow/{workflow_id}")
        async def get_workflow_endpoint(workflow_id: str):
            """Get detailed workflow information"""
            return await workflow_handlers.get_workflow(workflow_id)
        
        @app.post("/api/workflow/create")
        async def create_workflow_endpoint(payload: WorkflowExecutionPayload):
            """Create workflow without execution"""
            return await workflow_handlers.create_workflow(payload)
        
        @app.put("/api/workflow/{workflow_id}")
        async def update_workflow_endpoint(workflow_id: str, payload: WorkflowExecutionPayload):
            """Update existing workflow"""
            return await workflow_handlers.update_workflow(workflow_id, payload)
        
        @app.delete("/api/workflow/{workflow_id}")
        async def delete_workflow_endpoint(workflow_id: str):
            """Delete workflow"""
            return await workflow_handlers.delete_workflow(workflow_id)
        
        # ========== STATIC FILE ENDPOINTS (Frontend Integration) ==========
        
        # File upload endpoint
        @app.post("/api/upload")
        async def upload_file_endpoint(file: UploadFile = File(...), directory: str = "uploads"):
            """Upload file to server"""
            return await static_file_handlers.upload_file(file, directory)
        
        # File listing endpoints
        @app.get("/api/files/list")
        async def list_files_endpoint(directory: str = "reports", subdirectory: str = ""):
            """List files in directory"""
            return await static_file_handlers.list_files(directory, subdirectory)
        
        @app.get("/api/files/info/{filename}")
        async def get_file_info_endpoint(filename: str, directory: str = "reports"):
            """Get file information"""
            return await static_file_handlers.get_file_info(filename, directory)
        
        @app.delete("/api/files/{filename}")
        async def delete_file_endpoint(filename: str, directory: str = "uploads"):
            """Delete file"""
            return await static_file_handlers.delete_file(filename, directory)
        
        # Static file serving endpoints (critical for frontend)
        @app.get("/reports/{filename:path}")
        async def serve_report_file(filename: str):
            """Serve report files - CRITICAL for frontend"""
            return await static_file_handlers.serve_report_file(filename)
        
        @app.get("/assets/{filename:path}")
        async def serve_asset_file(filename: str):
            """Serve asset files"""
            return await static_file_handlers.serve_asset_file(filename)
        
        @app.get("/uploads/{filename:path}")
        async def serve_upload_file(filename: str):
            """Serve uploaded files"""
            return await static_file_handlers.serve_upload_file(filename)
        
        # WebSocket endpoint
        @app.websocket("/ws/events")
        async def websocket_endpoint(websocket: WebSocket):
            await self._handle_websocket_connection(websocket)
        
        # Legacy WebSocket endpoint (for compatibility)
        @app.websocket("/ws/workflow")
        async def legacy_websocket_endpoint(websocket: WebSocket):
            await self._handle_websocket_connection(websocket)
    
    def _setup_exception_handlers(self, app: FastAPI):
        """Setup exception handlers."""
        
        @app.exception_handler(Exception)
        async def global_exception_handler(request, exc):
            logger.error(f"Unhandled exception in {request.method} {request.url.path}: {exc}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": str(exc) if self.config.debug else "An unexpected error occurred",
                    "type": "server_error"
                }
            )
    
    def _setup_agent_card(self):
        """Setup dynamic agent card based on configuration."""
        if not self.config.agents:
            logger.warning("No agents configured, using default agent card")
            agent_name = "Praxis Agent"
        else:
            agent_name = self.config.agents[0].name
        
        # Determine the public URL (can be container hostname or configured URL)
        try:
            # Try to get hostname for container environments
            hostname = socket.gethostname()
            if hostname != "localhost" and hostname != "127.0.0.1":
                agent_url = f"http://{hostname}:{self.config.api.port}"
            else:
                agent_url = f"http://{self.config.api.host}:{self.config.api.port}"
        except:
            agent_url = f"http://{self.config.api.host}:{self.config.api.port}"
        
        # Create dynamic agent card with tools
        agent_card = create_dynamic_agent_card(
            name=agent_name,
            description="Advanced AI agent with P2P networking, MCP integration, and tool execution capabilities",
            url=agent_url,
            tools=self._get_available_tools_for_card(),
            provider=A2AProvider(
                name="Praxis",
                version="1.0.0", 
                description="Python implementation of Praxis agent framework",
                url="https://praxis.ai"
            )
        )
        
        # Add compatibility fields
        agent_card.version = "1.0.0"
        # Only declare HTTP for external publication and fallback. P2P JSON-RPC goes over libp2p and is not declared.
        agent_card.supported_transports = ["http"]
        
        # Set agent card in components
        api_gateway.set_agent_card(agent_card)
        get_request_handlers().set_agent_card(agent_card)
        
        logger.info(f"Agent card configured: {agent_name} at {agent_url}")
    
    def _get_available_tools_for_card(self):
        """Get tools that will be used for agent card generation."""
        # Get tools from API gateway if available
        if hasattr(api_gateway, 'available_tools') and api_gateway.available_tools:
            return api_gateway.available_tools
        
        # Get tools from request handlers if available
        if hasattr(get_request_handlers(), 'available_tools') and get_request_handlers().available_tools:
            return get_request_handlers().available_tools
            
        return []
    
    def _setup_tools(self):
        """Setup default tools."""
        default_tools = [
            ToolInfo(
                name="write_file",
                description="Write content to a file in the shared workspace",
                parameters={
                    "filename": {"type": "string", "description": "Name of the file to write"},
                    "content": {"type": "string", "description": "Content to write to the file"}
                },
                enabled=True
            ),
            ToolInfo(
                name="read_file",
                description="Read content from a file in the shared workspace",
                parameters={
                    "filename": {"type": "string", "description": "Name of the file to read"}
                },
                enabled=True
            ),
            ToolInfo(
                name="list_files",
                description="List files in the shared workspace",
                parameters={
                    "directory": {"type": "string", "description": "Directory to list (default: root)"}
                },
                enabled=True
            ),
            ToolInfo(
                name="python_analyzer",
                description="Execute Python code in an isolated Dagger container",
                parameters={
                    "code": {"type": "string", "description": "Python code to execute"},
                    "requirements": {"type": "array", "description": "Python packages to install"}
                },
                enabled=True
            )
        ]
        
        # Add configured tools
        for tool_config in self.config.tools:
            tool_info = ToolInfo(
                name=tool_config.name,
                description=tool_config.description,
                parameters=tool_config.parameters,
                enabled=tool_config.enabled
            )
            default_tools.append(tool_info)
        
        # Set tools in components
        api_gateway.set_available_tools(default_tools)
        get_request_handlers().set_available_tools(default_tools)
        
        # Update agent card with tools
        self._refresh_agent_card_with_tools(default_tools)
        
        logger.info(f"Tools configured: {len(default_tools)} tools available")
    
    def _refresh_agent_card_with_tools(self, tools):
        """Refresh the agent card with newly configured tools."""
        if not hasattr(self, '_base_agent_card_created'):
            # First time setup, agent card will be created with tools
            return
            
        # Get current agent card
        current_card = api_gateway.agent_card or get_request_handlers().agent_card
        if current_card:
            # Create updated card with tools
            updated_card = create_dynamic_agent_card(
                name=current_card.name,
                description=current_card.description,
                url=current_card.url,
                tools=tools,
                provider=current_card.provider
            )
            
            # Preserve compatibility fields
            updated_card.version = current_card.version
            updated_card.supported_transports = current_card.supported_transports
            
            # Update components
            api_gateway.set_agent_card(updated_card)
            get_request_handlers().set_agent_card(updated_card)
            
            logger.info(f"Agent card refreshed with {len(tools)} tools")
    
    async def _handle_websocket_connection(self, websocket: WebSocket):
        """Handle WebSocket connections with full integration."""
        try:
            # Handle connection through websocket manager
            connection_id = await websocket_manager.handle_connection(websocket)
            
            # Start message handling and event streaming
            async with trio.open_nursery() as nursery:
                nursery.start_soon(
                    trio_asyncio.aio_as_trio(websocket_manager.handle_client_messages),
                    connection_id
                )
                nursery.start_soon(
                    trio_asyncio.aio_as_trio(websocket_manager.handle_event_streaming),
                    connection_id
                )
        
        except Exception as e:
            logger.error(f"Error handling WebSocket connection: {e}")
    
    async def _startup(self):
        """Startup sequence."""
        try:
            # Start event bus
            if self._nursery:
                await event_bus.start(self._nursery)
            
            # Start WebSocket manager
            if self._nursery:
                await websocket_manager.start(self._nursery)
            
            # Initialize static file server and create sample files
            try:
                from praxis_sdk.api.static_server import static_file_server
                await static_file_server.create_sample_files()
                logger.info("Static file server initialized with sample files")
            except Exception as e:
                logger.warning(f"Error initializing static files: {e}")
            
            self._running = True
            logger.info("Praxis API server started successfully")
            
        except Exception as e:
            logger.error(f"Error during startup: {e}")
            raise
    
    async def _shutdown(self):
        """Shutdown sequence."""
        try:
            self._running = False
            
            # Stop WebSocket manager
            await websocket_manager.stop()
            
            # Stop event bus
            await event_bus.stop()
            
            logger.info("Praxis API server shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def run_with_trio(self):
        """Run server with trio event loop."""
        async def run_uvicorn():
            """Run Uvicorn server."""
            config = uvicorn.Config(
                self.app,
                host=self.config.api.host,
                port=self.config.api.port,
                log_level="info" if self.config.debug else "warning",
                access_log=self.config.debug,
                loop="none"  # We manage the event loop
            )
            
            server = uvicorn.Server(config)
            await server.serve()
        
        try:
            async with trio.open_nursery() as nursery:
                self._nursery = nursery
                
                logger.info(f"Starting Praxis API server on {self.config.api.host}:{self.config.api.port}")
                
                # Run Uvicorn server with trio_asyncio
                nursery.start_soon(trio_asyncio.aio_as_trio(run_uvicorn))
                
                # Setup signal handlers for graceful shutdown (only in main thread)
                try:
                    import threading
                    if threading.current_thread() is threading.main_thread():
                        def handle_signal(sig_num, frame):
                            logger.info(f"Received signal {sig_num}, initiating shutdown...")
                            nursery.cancel_scope.cancel()
                        signal.signal(signal.SIGINT, handle_signal)
                        signal.signal(signal.SIGTERM, handle_signal)
                except Exception as e:
                    logger.debug(f"Signal handler setup skipped: {e}")
        
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            logger.info("Server shutdown complete")
    
    def run(self):
        """Run server with trio-asyncio integration."""
        try:
            trio_asyncio.run(self.run_with_trio)
        except KeyboardInterrupt:
            logger.info("Application stopped by user")
        except Exception as e:
            logger.error(f"Application error: {e}")
            sys.exit(1)


# Create global server instance
server = PraxisAPIServer()

# Export FastAPI app for external use
app = server.app
