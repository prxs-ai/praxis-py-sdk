"""
Main Praxis Agent coordinator - Central orchestrator for all SDK components.
Manages P2P, MCP, API, and event bus with proper lifecycle coordination.
"""

import asyncio
import os
import signal
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import trio
import trio_asyncio
from loguru import logger

from .a2a.protocol import A2AProtocolHandler
from .a2a.models import A2AAgentCard, A2ACapabilities, A2ASkill
from .a2a.task_manager import TaskManager
from .api.server import PraxisAPIServer
from .bus import Event, EventBus, EventType, event_bus
from .config import AgentConfig, PraxisConfig, load_config
from .dsl.orchestrator import DSLOrchestrator
from .llm.client import LLMClient
from .mcp.server import MCPServer
from .p2p import create_simplified_p2p_service, SimplifiedP2PService
from .p2p.discovery import P2PDiscovery
from .execution import ExecutionEngine, DaggerExecutionEngine, LocalExecutionEngine, DockerSDKExecutionEngine, ToolContract, EngineType
from .execution.engine import test_dagger_availability
from .execution.contracts import ExecutionResult


class PraxisAgent:
    """
    Central Praxis Agent coordinator managing all subsystems.
    
    Handles component lifecycle, health monitoring, and coordination
    between P2P, MCP, API, and event bus systems.
    """
    
    def __init__(self, config: Optional[PraxisConfig] = None, agent_name: str = "orchestrator"):
        self.config = config or load_config()
        self.agent_name = agent_name
        self.agent_config = self._get_agent_config(agent_name)
        
        # Component state
        self._running = False
        self._startup_complete = False
        self._shutdown_in_progress = False
        self._health_status: Dict[str, bool] = {}
        
        # Core components
        self.event_bus = event_bus
        self.task_manager = TaskManager(self.event_bus)
        self.llm_client = LLMClient(self.config.llm)
        self.dsl_orchestrator = DSLOrchestrator(self, self.config)
        
        # Optional components (initialized in start())
        self.p2p_service: Optional[SimplifiedP2PService] = None
        self.p2p_discovery: Optional[P2PDiscovery] = None
        self.mcp_server: Optional[MCPServer] = None
        self.api_server: Optional[PraxisAPIServer] = None
        self.a2a_protocol: Optional[A2AProtocolHandler] = None
        
        # Execution engines and tool contracts
        self.execution_engines: Dict[EngineType, ExecutionEngine] = {}
        self.tool_contracts: Dict[str, ToolContract] = {}
        
        # Setup logging
        self._setup_logging()
        
        # Signal handling for graceful shutdown
        self._setup_signal_handlers()
        
        logger.info(f"Praxis Agent '{agent_name}' initialized")
    
    def _get_agent_config(self, agent_name: str) -> AgentConfig:
        """Get configuration for this specific agent."""
        agent_config = self.config.get_agent_config(agent_name)
        
        if not agent_config:
            # Create default agent config
            agent_config = AgentConfig(
                name=agent_name,
                description=f"Praxis agent: {agent_name}",
                tools=["filesystem", "python_exec", "web_search"],
                capabilities=["task_management", "tool_execution", "p2p_communication"]
            )
            self.config.add_agent(agent_config)
        
        return agent_config
    
    def _setup_logging(self):
        """Configure logging based on configuration."""
        log_config = self.config.logging
        
        # Remove default handler
        logger.remove()
        
        # Fix format if it's configured as "text" (causing spam)
        log_format = log_config.format
        if log_format == "text":
            log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        
        # Console logging
        logger.add(
            sink=lambda msg: print(msg, end=""),
            format=log_format,
            level=log_config.level.upper(),
            colorize=True
        )
        
        # File logging if enabled
        if log_config.file_enabled:
            log_path = Path(log_config.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.add(
                sink=log_path,
                format=log_format,
                level=log_config.level.upper(),
                rotation=log_config.file_rotation,
                retention=log_config.file_retention,
                serialize=log_config.json_logs
            )
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """Start the Praxis Agent and all subsystems."""
        if self._running:
            logger.warning("Agent is already running")
            return
        
        logger.info("Starting Praxis Agent...")
        self._running = True
        
        try:
            # Start event bus first (using asyncio, not trio)
            await self.event_bus.start()
            self._health_status["event_bus"] = True
            
            # Publish agent starting event
            await self.event_bus.publish_data(
                EventType.AGENT_STARTING,
                {"agent_name": self.agent_name, "config": self.agent_config.dict()},
                source=f"agent.{self.agent_name}"
            )
            
            # Start core components in order
            await self._start_core_components()
            logger.info("Core components started, now starting optional components...")
            
            # Start optional components
            await self._start_optional_components()
            logger.info("Optional components startup complete")
            
            # Mark startup complete
            self._startup_complete = True
            
            # Publish agent started event
            await self.event_bus.publish_data(
                EventType.AGENT_STARTED,
                {
                    "agent_name": self.agent_name,
                    "components": list(self._health_status.keys()),
                    "listen_addresses": self.get_listen_addresses(),
                    "peer_id": self.get_peer_id()
                },
                source=f"agent.{self.agent_name}"
            )
            
            logger.success(f"Praxis Agent '{self.agent_name}' started successfully")
            
            # Keep running until stop is called
            while self._running and not self._shutdown_in_progress:
                await asyncio.sleep(1)
                
                # Periodic health check
                if time.time() % 30 < 1:  # Every 30 seconds
                    await self._perform_health_check()
        
        except Exception as e:
            logger.error(f"Failed to start Praxis Agent: {e}")
            await self.event_bus.publish_data(
                EventType.AGENT_ERROR,
                {"error": str(e), "component": "startup"},
                source=f"agent.{self.agent_name}"
            )
            raise
    
    async def _start_core_components(self):
        """Start essential components."""
        
        # Start task manager (best-effort; optional nursery not provided here)
        try:
            await self.task_manager.start()  # Some implementations expect a nursery
            self._health_status["task_manager"] = True
            logger.info("Task manager started")
        except TypeError as e:
            # Gracefully continue if nursery is required; not critical for P2P
            self._health_status["task_manager"] = False
            logger.warning(f"Task manager start skipped (no nursery): {e}")
        
        # Initialize LLM client (best-effort; allow running without OpenAI)
        try:
            await self.llm_client.initialize()
            self._health_status["llm_client"] = True
            logger.info("LLM client initialized")
        except Exception as e:
            self._health_status["llm_client"] = False
            logger.warning(f"LLM client unavailable, continuing without LLM: {e}")
        
        # Start DSL orchestrator
        await self.dsl_orchestrator.start()
        self._health_status["dsl_orchestrator"] = True
        logger.info("DSL orchestrator started")
        
        # Initialize execution engines
        await self._init_execution_engines()
        
        # Load and register tools from configuration
        await self._load_and_register_tools_from_config()
    
    async def _init_execution_engines(self):
        """Initialize execution engines."""
        logger.info("Initializing execution engines...")
        
        # Always initialize Local execution engine
        try:
            local_engine = LocalExecutionEngine()
            self.execution_engines[EngineType.LOCAL] = local_engine
            self._health_status["local_execution_engine"] = True
            logger.info("Local execution engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize local execution engine: {e}")
            self._health_status["local_execution_engine"] = False
        
        # Initialize ONLY Dagger Engine - NO FALLBACK
        try:
            # Test if Dagger Engine is available
            dagger_available = await test_dagger_availability()
            if dagger_available:
                dagger_engine = DaggerExecutionEngine()
                self.execution_engines[EngineType.DAGGER] = dagger_engine
                self._health_status["dagger_execution_engine"] = True
                logger.success("✅ DAGGER ENGINE INITIALIZED! Container tools ready!")
            else:
                logger.error("❌ DAGGER ENGINE NOT AVAILABLE!")
                logger.error("Fix: Ensure gql==3.5.0 is installed (not gql>=4.0.0)")
                logger.error("Run: pip install --force-reinstall 'gql[all]==3.5.0'")
                self._health_status["dagger_execution_engine"] = False
        except ImportError as e:
            logger.error(f"❌ Dagger SDK import failed: {e}")
            logger.error("Install: pip install dagger-io==0.18.14")
            self._health_status["dagger_execution_engine"] = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize Dagger engine: {e}")
            self._health_status["dagger_execution_engine"] = False
        
        # Log available engines
        available_engines = list(self.execution_engines.keys())
        logger.info(f"Available execution engines: {available_engines}")
    
    async def _start_optional_components(self):
        """Start optional components based on configuration."""
        logger.info("Starting optional components...")
        
        # Start MCP server if enabled
        if self.config.mcp.enabled:
            try:
                external_eps: List[Any] = []
                try:
                    if self.config.agent and self.config.agent.external_mcp_endpoints:
                        external_eps = self.config.agent.external_mcp_endpoints
                except Exception:
                    external_eps = []
                # Also include config-level external endpoints
                try:
                    cfg_eps = self.config.mcp.external_endpoints or []
                    if cfg_eps:
                        external_eps = external_eps + cfg_eps
                except Exception:
                    pass
                self.mcp_server = MCPServer(self.config.mcp, self.event_bus, external_endpoints=external_eps)
                await self.mcp_server.start()
                
                # Register default Dagger tools if execution engines are available
                if EngineType.DAGGER in self.execution_engines:
                    await self.mcp_server.setup_default_dagger_tools(
                        agent=self, 
                        shared_path="/app/shared"
                    )
                
                self._health_status["mcp_server"] = True
                logger.info("MCP server started with Dagger tools")
            except Exception as e:
                logger.error(f"Failed to start MCP server: {e}")
        
        # Start P2P service if enabled
        if self.config.p2p.enabled:
            try:
                logger.info(f"Starting simplified P2P service with port {self.config.p2p.port}")
                self.p2p_service = create_simplified_p2p_service(self.config.p2p, self)
                logger.info("Simplified P2P service created, starting in background...")
                
                # Start P2P service in background thread using trio_asyncio
                import threading
                def run_p2p():
                    try:
                        self.p2p_service.start()
                    except Exception as e:
                        logger.error(f"P2P service error: {e}")
                
                p2p_thread = threading.Thread(target=run_p2p, daemon=True, name="P2P-Simplified-Thread")
                p2p_thread.start()
                
                # Give it a moment to initialize
                await asyncio.sleep(2)
                
                self._health_status["p2p_service"] = True
                logger.success(f"Simplified P2P service started successfully on port {self.config.p2p.port}")
                
                # Log peer information if available
                peer_id = self.p2p_service.get_peer_id()
                listen_addrs = self.p2p_service.get_listen_addresses()
                if peer_id:
                    logger.info(f"P2P Peer ID: {peer_id}")
                if listen_addrs:
                    logger.info(f"P2P listening on: {listen_addrs}")
                
                # P2P Discovery (mDNS) disabled - using direct P2P connections
                logger.info("P2P Discovery (mDNS) disabled - using direct P2P bootstrap connections")
                self._health_status["p2p_discovery"] = True  # Mark as OK since we're not using it
                
            except Exception as e:
                logger.error(f"Failed to start simplified P2P service: {e}")
                import traceback
                logger.error(f"P2P startup traceback: {traceback.format_exc()}")
                # Mark as failed but don't raise - agent can continue without P2P
                self._health_status["p2p_service"] = False
        else:
            logger.info("P2P service disabled in configuration")
        
        # Initialize A2A protocol
        agent_card = self._create_agent_card()
        self.a2a_protocol = A2AProtocolHandler(self.task_manager, agent_card, self.event_bus)
        self._health_status["a2a_protocol"] = True
        logger.info("A2A protocol initialized")
        
        # Start API server last (run FastAPI/uvicorn in background thread)
        try:
            from .api.server import server as api_server_instance

            def _run_api_server():
                try:
                    api_server_instance.run()
                except Exception as e:
                    logger.error(f"API server error: {e}")

            api_thread = threading.Thread(target=_run_api_server, daemon=True, name="API-Server-Thread")
            api_thread.start()

            self.api_server = api_server_instance
            # Attach agent context for P2P endpoints
            try:
                self.api_server.attach_context(self, self.event_bus)
            except Exception as e:
                logger.warning(f"Failed to attach agent context to API server: {e}")
            self._health_status["api_server"] = True
            logger.info("API server started")
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
    
    async def stop(self):
        """Stop the Praxis Agent and all subsystems gracefully."""
        if not self._running or self._shutdown_in_progress:
            return
        
        logger.info("Stopping Praxis Agent...")
        self._shutdown_in_progress = True
        
        # Publish agent stopping event
        await self.event_bus.publish_data(
            EventType.AGENT_STOPPING,
            {"agent_name": self.agent_name},
            source=f"agent.{self.agent_name}"
        )
        
        # Stop components in reverse order
        
        # Stop execution engines
        await self._stop_execution_engines()
        await self._stop_components()
        
        # Final cleanup
        self._running = False
        
        # Publish agent stopped event
        await self.event_bus.publish_data(
            EventType.AGENT_STOPPED,
            {"agent_name": self.agent_name},
            source=f"agent.{self.agent_name}"
        )
        
        # Stop event bus last
        await self.event_bus.stop()
        
        logger.info("Praxis Agent stopped")
    
    async def _stop_components(self):
        """Stop all components gracefully."""
        
        # Stop API server first (best-effort; background thread will exit on process stop)
        if self.api_server:
            try:
                # Current API server implementation runs in background thread without explicit stop
                logger.info("API server stop requested (no-op)")
            except Exception as e:
                logger.error(f"Error stopping API server: {e}")
        
        # Stop P2P service
        if self.p2p_service:
            try:
                self.p2p_service.stop()  # Synchronous call
                logger.info("Simplified P2P service stopped")
            except Exception as e:
                logger.error(f"Error stopping simplified P2P service: {e}")
        
        # Stop MCP server
        if self.mcp_server:
            try:
                await self.mcp_server.stop()
                logger.info("MCP server stopped")
            except Exception as e:
                logger.error(f"Error stopping MCP server: {e}")
        
        # Stop DSL orchestrator
        if self.dsl_orchestrator:
            try:
                await self.dsl_orchestrator.stop()
                logger.info("DSL orchestrator stopped")
            except Exception as e:
                logger.error(f"Error stopping DSL orchestrator: {e}")
        
        # Stop task manager
        if self.task_manager:
            try:
                await self.task_manager.stop()
                logger.info("Task manager stopped")
            except Exception as e:
                logger.error(f"Error stopping task manager: {e}")
    
    async def _perform_health_check(self):
        """Perform periodic health check of all components."""
        for component, status in self._health_status.items():
            try:
                # Perform specific health checks per component
                if component == "p2p_service" and self.p2p_service:
                    # Check if P2P service is running
                    if not self.p2p_service.running and status:
                        logger.warning("Simplified P2P service stopped unexpectedly")
                        # Could implement restart logic here
                
                elif component == "api_server" and self.api_server:
                    # API server health check would go here
                    pass
                
            except Exception as e:
                logger.error(f"Health check failed for {component}: {e}")
    
    # Public API methods for external access
    
    def _create_agent_card(self) -> A2AAgentCard:
        """Create an A2A agent card for protocol use."""
        # Create A2A specification-compliant capabilities
        capabilities = A2ACapabilities(
            streaming=True,
            push_notifications=True,
            state_transition_history=True
        )
        
        # Create skills based on available tools and agent capabilities
        skills = []
        
        # File operations skill
        skills.append(A2ASkill(
            id="file-operations",
            name="File Operations",
            description="Read, write, and manipulate files in shared workspace",
            tags=["filesystem", "io", "files"]
        ))
        
        # Code execution skill
        skills.append(A2ASkill(
            id="code-execution", 
            name="Python Code Execution",
            description="Execute Python code and scripts in isolated Dagger containers",
            tags=["python", "execution", "dagger", "code"]
        ))
        
        # Data processing skill
        skills.append(A2ASkill(
            id="data-processing",
            name="Data Processing",
            description="Process and analyze data using various tools",
            tags=["data", "analysis", "processing"]
        ))
        
        # Workflow orchestration skill (for orchestrator agents)
        if self.agent_name == "orchestrator":
            skills.append(A2ASkill(
                id="workflow-orchestration",
                name="Workflow Orchestration",
                description="Coordinate complex multi-step workflows across agents using DSL and LLM",
                tags=["orchestration", "workflow", "dsl", "llm"]
            ))
        
        # Create provider information
        from .a2a.models import A2AProvider
        provider = A2AProvider(
            name="Praxis SDK",
            version="1.0.0", 
            description="Python implementation of Praxis agent framework with P2P networking",
            url="https://github.com/praxis-ai/praxis-python"
        )
        
        # Create agent card
        return A2AAgentCard(
            name=self.agent_config.name,
            version="1.0.0",
            protocol_version="0.2.9",
            preferred_transport="JSONRPC",
            url=f"http://{self.config.api.host}:{self.config.api.port}",
            description=self.agent_config.description,
            skills=skills,
            capabilities=capabilities,
            supported_transports=["http"],
            security_schemes={},  # Empty for now, can be enhanced later
            provider=provider
        )
    
    def get_agent_card(self) -> Dict[str, Any]:
        """Get the agent's A2A-compliant capability card."""
        # Return the A2A-compliant card as a dictionary
        a2a_card = self._create_agent_card()
        return a2a_card.model_dump(by_alias=True)
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from registered contracts and MCP, with valid JSON Schema.

        Returns tools where "parameters" is a JSON Schema object suitable for
        LLM tool/function calling: {type: "object", properties: {...}, required: [...]}
        """
        tools: List[Dict[str, Any]] = []

        # Registered tool contracts → JSON Schema
        for contract in self.tool_contracts.values():
            properties: Dict[str, Any] = {}
            required: List[str] = []

            for param in contract.parameters:
                properties[param.name] = {
                    "type": param.type or "string",
                    "description": param.description or "Parameter",
                }
                if getattr(param, "default", None) is not None:
                    properties[param.name]["default"] = param.default
                if param.required:
                    required.append(param.name)

            parameters_schema: Dict[str, Any] = {
                "type": "object",
                "properties": properties,
                "required": required,
            }

            tools.append(
                {
                    "name": contract.name,
                    "description": contract.description,
                    "engine": contract.engine.value,
                    "parameters": parameters_schema,
                }
            )

        # MCP server tools (already shaped as JSON Schema)
        if self.mcp_server:
            mcp_tools = self.mcp_server.get_available_tools()
            tools.extend(mcp_tools)

        return tools
    
    def get_peer_id(self) -> Optional[str]:
        """Get P2P peer ID if P2P is enabled."""
        if self.p2p_service:
            return self.p2p_service.get_peer_id()
        return None
    
    def get_listen_addresses(self) -> List[str]:
        """Get all listen addresses."""
        addresses = []
        
        # API server address
        if self.api_server:
            addresses.append(f"http://{self.config.api.host}:{self.config.api.port}")
        
        # P2P addresses
        if self.p2p_service:
            addresses.extend(self.p2p_service.get_listen_addresses())
        
        return addresses
    
    async def dispatch_a2a_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch A2A request - called from P2P handlers (trio context).
        This method will be called from trio context via aio_as_trio bridge.
        """
        if not self.a2a_protocol:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32000,
                    "message": "A2A protocol not initialized"
                }
            }
        
        response = await self.a2a_protocol.handle_request(request)
        # Ensure plain dict for P2P JSON transport
        try:
            return response.model_dump(by_alias=True)
        except Exception:
            # Fallback in case response is already a dict-like
            if isinstance(response, dict):
                return response
            # Last resort: basic serialization
            from pydantic import BaseModel
            if isinstance(response, BaseModel):
                return response.dict()
            return response
    
    async def execute_dsl_command(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a DSL command."""
        return await self.dsl_orchestrator.execute_command(command, context or {})
    
    async def invoke_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a tool by name using registered tool contracts and execution engines.
        
        This is the core method for the DSL → LLM → Tool Selection → Execution flow.
        """
        logger.info(f"🔧 TOOL INVOCATION: '{tool_name}' on agent '{self.agent_name}'")
        logger.info(f"   📥 Tool Arguments: {arguments}")
        
        # First, try to find tool in registered tool contracts
        if tool_name in self.tool_contracts:
            contract = self.tool_contracts[tool_name]
            logger.info(f"   📋 TOOL CONTRACT FOUND: {tool_name} -> {contract.engine.value}")
            
            try:
                # Execute using appropriate engine
                engine = self.execution_engines.get(contract.engine)
                if not engine:
                    logger.error(f"   ❌ ENGINE NOT AVAILABLE: {contract.engine.value}")
                    return {
                        "success": False,
                        "error": f"Execution engine {contract.engine.value} not available"
                    }
                
                logger.info(f"   🚀 EXECUTING VIA {contract.engine.value.upper()} ENGINE...")
                
                # Execute through appropriate engine
                result = await engine.execute(contract, arguments)
                
                # Ensure results are saved to shared/reports for all Dagger tools
                await self._ensure_results_saved_to_reports(tool_name, result, arguments, contract.engine)
                
                logger.info(f"   ✅ TOOL EXECUTION SUCCESS: {tool_name}")
                logger.info(f"   📤 Result: {str(result)[:200]}...")
                
                return {
                    "success": True,
                    "tool": tool_name,
                    "engine": contract.engine.value,
                    "result": result.output if hasattr(result, 'output') else result,
                    "execution_time": getattr(result, 'execution_time', None)
                }
                
            except Exception as e:
                logger.error(f"   ❌ TOOL CONTRACT EXECUTION FAILED: {tool_name} - {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "tool": tool_name,
                    "engine": contract.engine.value
                }
        
        # Fallback to MCP server for tools not in contracts
        if self.mcp_server:
            try:
                logger.info(f"   🚀 ROUTING TO MCP SERVER...")
                result = await self.mcp_server.invoke_tool(tool_name, arguments)
                logger.info(f"   ✅ MCP TOOL EXECUTION SUCCESS: {tool_name}")
                logger.info(f"   📤 Result: {str(result)[:200]}...")
                return {
                    "success": True,
                    "tool": tool_name,
                    "engine": "mcp",
                    "result": result
                }
            except Exception as e:
                logger.error(f"   ❌ MCP TOOL EXECUTION FAILED: {tool_name} - {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "tool": tool_name,
                    "engine": "mcp"
                }
        
        logger.error(f"   ❌ TOOL NOT FOUND: Tool {tool_name} not available in contracts or MCP server")
        return {
            "success": False,
            "error": f"Tool {tool_name} not found in tool contracts or MCP server",
            "available_tools": list(self.tool_contracts.keys())
        }
    
    def is_healthy(self) -> bool:
        """Check if agent is healthy."""
        return self._running and self._startup_complete and all(self._health_status.values())
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status."""
        return {
            "agent_name": self.agent_name,
            "running": self._running,
            "startup_complete": self._startup_complete,
            "healthy": self.is_healthy(),
            "components": self._health_status,
            "peer_id": self.get_peer_id(),
            "listen_addresses": self.get_listen_addresses(),
            "uptime": time.time() if self._startup_complete else 0
        }
    
    async def _stop_execution_engines(self):
        """Stop all execution engines gracefully."""
        logger.info("Stopping execution engines...")
        
        for engine_type, engine in self.execution_engines.items():
            try:
                await engine.cleanup()
                logger.info(f"Execution engine {engine_type} stopped")
            except Exception as e:
                logger.error(f"Error stopping execution engine {engine_type}: {e}")
        
        self.execution_engines.clear()
    
    async def execute_tool(
        self, 
        contract: ToolContract, 
        args: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """Execute tool using appropriate execution engine.
        
        Args:
            contract: Tool contract defining execution parameters
            args: Arguments to pass to the tool
            timeout: Optional timeout in seconds
            
        Returns:
            ExecutionResult with execution details
        """
        engine = self.execution_engines.get(contract.engine)
        if not engine:
            logger.error(f"Engine {contract.engine} not available")
            return ExecutionResult.error_result(
                f"Engine {contract.engine} not available"
            )
        
        logger.info(f"Executing tool {contract.name} with {contract.engine} engine")
        
        try:
            result = await engine.execute(contract, args, timeout)
            
            # Log execution result
            if result.success:
                logger.info(f"Tool {contract.name} executed successfully")
            else:
                logger.warning(f"Tool {contract.name} failed: {result.error}")
            
            # Publish execution event
            await self.event_bus.publish_data(
                EventType.TOOL_EXECUTED,
                {
                    "tool_name": contract.name,
                    "engine": str(contract.engine),
                    "success": result.success,
                    "duration": result.duration,
                    "error": result.error
                },
                source=f"agent.{self.agent_name}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution failed with exception: {e}")
            error_result = ExecutionResult.error_result(
                error=f"Tool execution failed: {str(e)}"
            )
            
            await self.event_bus.publish_data(
                EventType.TOOL_EXECUTED,
                {
                    "tool_name": contract.name,
                    "engine": str(contract.engine),
                    "success": False,
                    "error": str(e)
                },
                source=f"agent.{self.agent_name}"
            )
            
            return error_result
    
    def get_available_engines(self) -> List[EngineType]:
        """Get list of available execution engines."""
        return list(self.execution_engines.keys())
    
    def register_tool_contract(self, contract: ToolContract):
        """Register a tool contract for later execution.
        
        This method allows external components to register tool contracts
        that can be used by the DSL orchestrator and other components.
        """
        self.tool_contracts[contract.name] = contract
        logger.info(f"Tool contract registered: {contract.name} ({contract.engine.value})")
    
    async def _load_and_register_tools_from_config(self):
        """Load tools from agent configuration and register them as ToolContract objects."""
        logger.info("Loading tools from configuration...")
        
        # Load tools from agent config using new format
        agent_config_raw = None
        # Try both paths for config file (container and local)
        config_paths = [
            f"/app/configs/{self.agent_name}.yaml",  # Container path
            f"configs/{self.agent_name}.yaml",       # Local path
            self.config_file if hasattr(self, 'config_file') else None  # Path from config
        ]
        
        for config_path in config_paths:
            if config_path and os.path.exists(config_path):
                logger.info(f"Loading tools from config: {config_path}")
                with open(config_path, 'r') as f:
                    import yaml
                    agent_config_raw = yaml.safe_load(f)
                break
        
        if not agent_config_raw or 'agent' not in agent_config_raw:
            logger.warning(f"No agent configuration found for {self.agent_name}")
            return
        
        agent_data = agent_config_raw['agent']
        tools = agent_data.get('tools', [])
        
        for tool_config in tools:
            try:
                await self._register_tool_from_config(tool_config)
            except Exception as e:
                logger.error(f"Failed to register tool {tool_config.get('name', 'unknown')}: {e}")
    
    async def _register_tool_from_config(self, tool_config: Dict[str, Any]):
        """Register a single tool from configuration as a ToolContract."""
        name = tool_config.get('name')
        description = tool_config.get('description', '')
        engine = tool_config.get('engine', 'dagger')
        params = tool_config.get('params', [])
        engine_spec = tool_config.get('engineSpec', {})
        
        if not name:
            logger.warning("Tool configuration missing name, skipping")
            return
        
        # Convert params to ToolParameter objects
        from .execution.contracts import ToolParameter
        parameters = []
        for param in params:
            parameters.append(ToolParameter(
                name=param['name'],
                type=param['type'],
                description=param.get('description', ''),
                required=str(param.get('required', False)).lower() == 'true'
            ))
        
        # Create appropriate engine spec based on engine type
        if engine == 'dagger':
            from .execution.contracts import DaggerEngineSpec
            dagger_spec = DaggerEngineSpec(
                image=engine_spec.get('image', 'python:3.11-slim'),
                command=engine_spec.get('command', ['python', '-c', 'print("Hello World")']),
                mounts=engine_spec.get('mounts', {}),
                env_passthrough=engine_spec.get('env_passthrough', [])
            )
            
            contract = ToolContract(
                name=name,
                description=description,
                parameters=parameters,
                engine=EngineType.DAGGER,
                engine_spec=dagger_spec.dict()
            )
        elif engine == 'remote-mcp':
            from .execution.contracts import RemoteMCPEngineSpec
            mcp_spec = RemoteMCPEngineSpec(
                address=engine_spec.get('address', 'http://localhost:8080')
            )
            
            contract = ToolContract(
                name=name,
                description=description,
                parameters=parameters,
                engine=EngineType.REMOTE_MCP,
                engine_spec=mcp_spec.dict()
            )
        else:
            # Default to local execution
            from .execution.contracts import LocalEngineSpec
            local_spec = LocalEngineSpec(
                command=['echo', 'Not implemented'],
                shell=False
            )
            
            contract = ToolContract(
                name=name,
                description=description,
                parameters=parameters,
                engine=EngineType.LOCAL,
                engine_spec=local_spec.dict()
            )
        
        self.register_tool_contract(contract)
        logger.success(f"Registered tool: {name} ({engine})")
    
    async def _ensure_results_saved_to_reports(self, tool_name: str, result: Any, arguments: Dict[str, Any], engine: Optional[EngineType] = None):
        """Save tool results to shared/reports for Dagger tools (and others when applicable).

        - Always saves for Dagger engine tools.
        - Saves both raw stdout (txt) and structured report (json) when possible.
        - Uses configured shared_dir if available, defaults to /app/shared.
        """
        try:
            # Only enforce for Dagger tools per requirement
            if engine is not None and engine != EngineType.DAGGER:
                return

            import json
            import datetime
            from pathlib import Path

            # Determine reports directory from config shared_dir
            shared_dir = self.config.shared_dir or "/app/shared"
            reports_dir = Path(shared_dir) / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            # Normalize result content
            if hasattr(result, 'output'):
                content = result.output
            else:
                content = result

            # Build timestamped filenames
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"{tool_name}_{timestamp}"
            text_path = reports_dir / f"{base_name}.txt"
            json_path = reports_dir / f"{base_name}.json"

            # Try to parse content as JSON for pretty saving
            parsed_json = None
            if isinstance(content, (dict, list)):
                parsed_json = content
            elif isinstance(content, str):
                try:
                    parsed_json = json.loads(content)
                except Exception:
                    parsed_json = None

            # Write raw text output
            try:
                text_to_write = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(text_to_write)
            except Exception as e:
                logger.warning(f"   ⚠️ Could not write raw output file {text_path}: {e}")

            # Write structured JSON report
            try:
                report_data = {
                    "tool": tool_name,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    "arguments": arguments,
                    "agent": self.agent_name,
                    "engine": str(engine) if engine else None,
                    "result": parsed_json if parsed_json is not None else content,
                }
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2, ensure_ascii=False)
                logger.info(f"   📝 REPORT SAVED: {json_path}")
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to save JSON report for {tool_name}: {e}")

        except Exception as outer_err:
            logger.warning(f"   ⚠️ Report saving skipped due to error: {outer_err}")
    
    async def create_python_analyzer_tool(self, shared_path: str = "/app/shared") -> ToolContract:
        """Create Python analyzer tool contract similar to Go implementation.
        
        This recreates the python_analyzer tool from the Go codebase using
        the Python Docker image and shared volume mounting.
        """
        return ToolContract.create_dagger_tool(
            name="python_analyzer",
            image="praxis-python:latest",
            command=["python", "/app/analyzer.py"],
            mounts={shared_path: "/shared"},
            env={
                "PYTHONPATH": "/app",
                "LOG_LEVEL": "INFO",
                "ANALYSIS_MODE": "full"
            },
            env_passthrough=["OPENAI_API_KEY", "DEBUG"],
            working_dir="/app",
            timeout=300,
            description="Analyze Python code and generate reports"
        )
    
    async def create_file_writer_tool(self, shared_path: str = "/app/shared") -> ToolContract:
        """Create file writer tool for creating files in shared directory."""
        return ToolContract.create_dagger_tool(
            name="file_writer", 
            image="busybox:latest",
            command=["sh", "-c", "echo \"$content\" > \"/shared/$filename\""],
            mounts={shared_path: "/shared"},
            env={},
            env_passthrough=[],
            working_dir="/shared",
            timeout=30,
            description="Write content to file in shared directory"
        )


# Convenience function for creating and running agent
async def run_agent(config_file: Optional[str] = None, agent_name: str = "orchestrator"):
    """Create and run a Praxis Agent."""
    config = load_config(config_file)
    agent = PraxisAgent(config, agent_name)
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await agent.stop()


# Main entry point
async def main():
    """Main entry point for the Praxis Agent."""
    import sys
    
    config_file = sys.argv[1] if len(sys.argv) > 1 else None
    agent_name = sys.argv[2] if len(sys.argv) > 2 else "orchestrator"
    
    await run_agent(config_file, agent_name)


if __name__ == "__main__":
    asyncio.run(main())
