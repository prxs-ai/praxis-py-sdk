"""Enhanced DSL Orchestrator with Advanced DSL Processing Engine integration.
Handles both simple DSL commands, complex workflows, and LLM-orchestrated tool execution.
Integrates with new parser, tokenizer, AST builder, and validation engine.
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel

from ..bus import EventBus, EventType
from ..config import PraxisConfig
from .planner import NetworkContext, TaskPlanner
from .types import ExecutionContext, ExecutionResult


class ToolCall(BaseModel):
    """Tool call model for OpenAI function calling."""

    name: str
    arguments: dict[str, Any]


class DSLOrchestrator:
    """Enhanced DSL command orchestrator with Advanced DSL Engine integration.
    Supports:
    - Advanced DSL commands (CALL, PARALLEL, SEQUENCE, WORKFLOW, etc.)
    - Legacy simple DSL commands
    - Natural language processing with LLM
    - Tool execution caching and validation
    - Workflow generation from natural language
    - A2A task system integration
    """

    def __init__(self, agent: "PraxisAgent", config: PraxisConfig):
        self.agent = agent
        self.config = config
        self.event_bus = agent.event_bus

        # OpenAI client
        self.llm_client = AsyncOpenAI(
            api_key=config.llm.api_key, base_url=config.llm.base_url
        )

        # Task Planner for natural language processing (kept for planning context only)
        self.task_planner = TaskPlanner(self.llm_client, config.llm.model)

        # No AST/DSL parsing path: all commands go through LLM orchestration and tool-calling

        self._running = False

        logger.info("Enhanced DSL Orchestrator initialized with Advanced DSL Engine")

    async def start(self):
        """Start DSL orchestrator."""
        self._running = True
        logger.info("DSL orchestrator started")

    async def stop(self):
        """Stop DSL orchestrator."""
        self._running = False
        logger.info("DSL orchestrator stopped")

    async def execute_command(
        self, command: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute ANY command through LLM orchestration with P2P agent coordination.

        ALL commands (simple, complex, natural language) go through LLM to decide:
        - Which tools to use
        - Which agents have those tools
        - How to coordinate execution via P2P

        Args:
            command: Any command or natural language request
            context: Execution context with metadata

        Returns:
            Execution result from LLM orchestration

        """
        # Log command execution
        await self.event_bus.publish_data(
            EventType.DSL_COMMAND_RECEIVED, {"command": command, "context": context}
        )

        try:
            # ALL COMMANDS GO THROUGH LLM - NO PATTERN MATCHING OR TOKENIZATION
            logger.info(f"🔥 DSL REQUEST RECEIVED: '{command}'")
            logger.info(f"📋 CONTEXT: {context}")
            logger.info("🤖 ROUTING → LLM Orchestration (no pattern matching)")

            result = await self._execute_with_llm_orchestration(command, context)

            await self.event_bus.publish_data(
                EventType.DSL_COMMAND_COMPLETED, {"command": command, "result": result}
            )

            return result

        except Exception as e:
            logger.error(f"Error executing command '{command}': {e}")
            error_result = {"success": False, "error": str(e)}

            await self.event_bus.publish_data(
                EventType.DSL_COMMAND_COMPLETED, {"command": command, "error": str(e)}
            )

            return error_result

    async def _execute_with_llm_orchestration(
        self, command: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute command using pure LLM orchestration with P2P agent coordination.

        Process:
        1. LLM analyzes the command
        2. LLM gets available agents and their tools via P2P discovery
        3. LLM selects best agent(s) for each tool
        4. Execute tools via P2P calls
        5. LLM coordinates results
        """
        logger.info("🔍 P2P DISCOVERY: Scanning network for available agents...")

        # Get available P2P agents and their capabilities
        available_agents = await self._discover_p2p_agents()
        local_tools = await self._get_local_tools()

        logger.info(f"🌐 AGENTS DISCOVERED: {len(available_agents)} agents in network")
        for agent in available_agents:
            agent_tools = len(agent.get("tools", []))
            logger.info(
                f"   👤 {agent.get('name', 'unknown')} ({agent.get('type', 'unknown')}): {agent_tools} tools"
            )

        # Prepare comprehensive context for LLM
        agent_context = self._build_agent_context(available_agents, local_tools)

        # Get available tools from all agents (local + P2P)
        all_tools = await self._get_all_available_tools(available_agents, local_tools)

        logger.info(
            f"🔧 TOTAL TOOLS AVAILABLE: {len(all_tools)} tools across all agents"
        )

        # Convert tools to OpenAI function format
        functions = self._convert_tools_to_functions(all_tools)

        # Enhanced system prompt for P2P orchestration
        system_prompt = f"""
Вы - умный оркестратор агентов в P2P сети. Ваша задача:

1. АНАЛИЗ: Понять что хочет пользователь из команды/фразы
2. ПЛАНИРОВАНИЕ: Выбрать нужные инструменты и агентов
3. ОРКЕСТРАЦИЯ: Координировать выполнение через P2P сеть

ДОСТУПНЫЕ АГЕНТЫ И ИНСТРУМЕНТЫ:
{agent_context}

ПРАВИЛА:
- Любая фраза пользователя - это задача для выполнения
- Выбирайте лучших агентов для каждого инструмента
- Координируйте выполнение в логическом порядке
- Собирайте и объединяйте результаты

Отвечайте на любом языке, на котором обратился пользователь.
"""

        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command},
        ]

        # Add context if available
        if context:
            messages[0]["content"] += (
                f"\n\nКОНТЕКСТ ВЫПОЛНЕНИЯ: {json.dumps(context, ensure_ascii=False)}"
            )

        try:
            logger.info(f"🧠 LLM ANALYSIS: Sending to {self.config.llm.model}")
            logger.info(f"   📨 User Request: '{command}'")
            logger.info(f"   🛠️  Available Functions: {len(functions)} tools")

            # Debug: log first function to see the structure
            if functions:
                logger.debug(
                    f"   📋 First function structure: {json.dumps(functions[0], indent=2, ensure_ascii=False)}"
                )

            # Call LLM with function calling
            try:
                response = await self.llm_client.chat.completions.create(
                    model=self.config.llm.model,
                    messages=messages,
                    tools=functions if functions else None,
                    tool_choice="auto" if functions else None,
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens,
                )
            except Exception as e:
                logger.error(f"LLM call failed, using heuristic fallback: {e}")
                # Try heuristic tool selection (computer-use)
                fallback = await self._heuristic_fallback(command, available_agents)
                return {
                    "success": fallback.get("success", False),
                    "method": "heuristic_fallback",
                    "result": fallback,
                }

            logger.info("✅ LLM RESPONSE RECEIVED")

            # Process LLM response and execute tools
            return await self._process_llm_orchestration_response(
                response, messages, available_agents, original_command=command
            )

        except Exception as e:
            logger.error(f"Error in LLM orchestration: {e}")
            return {"success": False, "error": str(e), "method": "llm_orchestration"}

    # REMOVED: _try_simple_dsl - all commands go through LLM orchestration

    # REMOVED: Old _execute_with_llm method - replaced with _execute_with_llm_orchestration

    async def _execute_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a specific tool."""
        # Publish progress event
        await self.event_bus.publish_data(
            EventType.DSL_COMMAND_PROGRESS, {"tool": tool_name, "arguments": arguments}
        )

        # Execute through agent
        return await self.agent.invoke_tool(tool_name, arguments)

    # REMOVED: _execute_read, _execute_write, _execute_list - all handled by LLM orchestration

    async def execute_workflow(
        self, dsl_workflow: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a complete DSL workflow (multi-line DSL commands).

        This method is used by the LLM Workflow Planner for executing
        generated workflow plans.

        Args:
            dsl_workflow: Multi-line DSL workflow
            context: Optional execution context

        Returns:
            Consolidated execution result

        """
        if not context:
            context = {}

        logger.info(
            f"Executing DSL workflow with {len(dsl_workflow.splitlines())} commands"
        )

        # Split workflow into individual commands
        lines = dsl_workflow.strip().split("\n")
        commands = []

        for line in lines:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith("#"):
                commands.append(line)

        if not commands:
            return {"success": True, "message": "Empty workflow - nothing to execute"}

        # Execute commands sequentially
        results = []
        workflow_context = context.copy()

        try:
            for i, command in enumerate(commands):
                logger.debug(f"Executing command {i + 1}/{len(commands)}: {command}")

                # Add step information to context
                step_context = {
                    **workflow_context,
                    "step": i + 1,
                    "total_steps": len(commands),
                    "workflow_id": context.get(
                        "workflow_id",
                        f"workflow_{int(asyncio.get_event_loop().time())}",
                    ),
                }

                # Execute individual command
                result = await self.execute_command(command, step_context)

                # Track result
                step_result = {
                    "step": i + 1,
                    "command": command,
                    "result": result,
                    "success": result.get("success", False),
                }

                results.append(step_result)

                # If command failed and not configured to continue on error
                if not result.get("success", False) and not context.get(
                    "continue_on_error", False
                ):
                    logger.error(
                        f"Workflow stopped at step {i + 1} due to error: {result.get('error', 'Unknown error')}"
                    )
                    break

                # Update workflow context with any outputs from this step
                if "output" in result:
                    workflow_context[f"step_{i + 1}_output"] = result["output"]

            # Calculate overall success
            successful_steps = sum(1 for r in results if r["success"])
            total_steps = len(results)

            workflow_result = {
                "success": successful_steps == total_steps,
                "total_steps": total_steps,
                "successful_steps": successful_steps,
                "failed_steps": total_steps - successful_steps,
                "results": results,
                "execution_time": sum(
                    r["result"].get("execution_time", 0) for r in results
                ),
                "workflow_summary": f"Executed {successful_steps}/{total_steps} steps successfully",
            }

            # Add failure details if any steps failed
            if successful_steps < total_steps:
                failed_steps = [r for r in results if not r["success"]]
                workflow_result["failures"] = [
                    {
                        "step": r["step"],
                        "command": r["command"],
                        "error": r["result"].get("error", "Unknown error"),
                    }
                    for r in failed_steps
                ]

            logger.success(
                f"Workflow completed: {successful_steps}/{total_steps} steps successful"
            )
            return workflow_result

        except Exception as e:
            logger.error(f"Fatal error executing workflow: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": results,
                "workflow_summary": f"Workflow failed at step {len(results) + 1}",
            }

    def _get_help(self, topic: str | None) -> dict[str, Any]:
        """Get help information."""
        if topic:
            # Topic-specific help
            help_topics = {
                "dsl": "DSL Commands:\n- read <path>\n- write <path> <content>\n- list [path]\n- exec <tool> <args>\n- tool <tool> <args>\n- help [topic]",
                "tools": f"Available tools: {', '.join([t['name'] for t in self.agent.get_available_tools()])}",
                "commands": "Use natural language or DSL commands. The LLM will select appropriate tools.",
                "workflow": "Multi-line DSL workflows are supported. Use execute_workflow() for complex workflows.",
            }

            help_text = help_topics.get(topic, f"No help available for '{topic}'")
            return {"success": True, "help": help_text}

        # General help
        help_text = """
Praxis Agent Help:

You can use either:
1. Natural language commands (e.g., "create a file named test.txt with hello world")
2. DSL commands (e.g., "write test.txt hello world")
3. Multi-line DSL workflows for complex operations

DSL Commands:
- read <path> - Read a file
- write <path> <content> - Write to a file
- list [path] - List directory contents
- exec <tool> <args> - Execute a tool
- tool <tool> <args> - Execute a tool
- help [topic] - Get help

The agent uses AI to understand your intent and execute the appropriate tools.
Multi-line workflows are executed sequentially with error handling.

For more help: help dsl, help tools, help commands, help workflow
"""
        return {"success": True, "help": help_text.strip()}

    # REMOVED: _is_advanced_dsl - no more pattern checking, LLM handles all commands

    # REMOVED: _execute_with_advanced_engine - replaced with pure LLM orchestration

    async def generate_workflow_from_natural_language(
        self, user_request: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Generate workflow from natural language using Advanced DSL Engine."""
        # Build network context
        network_context = NetworkContext()

        # Add available tools
        if hasattr(self.agent, "get_available_tools"):
            tools = self.agent.get_available_tools()
            for tool in tools:
                network_context.add_tool(tool)

        # Add agent info if available
        if hasattr(self.agent, "peer_id"):
            agent_info = {
                "id": self.agent.peer_id,
                "tools": [tool.get("name") for tool in tools if "name" in tool],
                "load": 0.1,  # Default low load
            }
            network_context.add_agent(agent_info)

        try:
            # Generate workflow plan
            workflow_plan = (
                await self.advanced_parser.generate_workflow_from_natural_language(
                    user_request, network_context
                )
            )

            if workflow_plan:
                logger.info(
                    f"Generated workflow plan: {workflow_plan.id} with {len(workflow_plan.nodes)} nodes"
                )
                return workflow_plan.to_dict()

            return None

        except Exception as e:
            logger.error(f"Workflow generation failed: {e}")
            return None

    def get_advanced_engine_stats(self) -> dict[str, Any]:
        """Get statistics from Advanced DSL Engine."""
        return self.advanced_parser.get_stats()

    def clear_advanced_engine_cache(self) -> None:
        """Clear cache in Advanced DSL Engine."""
        self.advanced_parser.clear_cache()
        logger.info("Advanced DSL Engine cache cleared")

    # ====== NEW LLM-ONLY P2P ORCHESTRATION METHODS ======

    async def _discover_p2p_agents(self) -> list[dict[str, Any]]:
        """Discover available P2P agents and their capabilities."""
        try:
            agents = []

            # Get agents from P2P service if available
            if hasattr(self.agent, "p2p_service") and self.agent.p2p_service:
                try:
                    # Build agents from peer cards + tools cache
                    p2p = self.agent.p2p_service

                    # Prefer actively connected peers; if none, fall back to peers known via exchange cache
                    peer_ids = list(p2p.get_connected_peers())
                    if not peer_ids:
                        # Fallback: include peers that have exchanged cards/tools even if we are responder only
                        try:
                            peer_ids = list((p2p.get_all_peer_tools() or {}).keys())
                        except Exception:
                            peer_ids = list(
                                (getattr(p2p, "peer_tools", {}) or {}).keys()
                            )

                    # Build agent entries
                    for peer_id in peer_ids:
                        card = p2p.get_peer_card(peer_id) or {}
                        peer_name = card.get("name", peer_id)
                        tools = p2p.get_peer_tools(peer_id) or []
                        agents.append(
                            {
                                "id": peer_id,
                                "name": peer_name,
                                "type": "p2p",
                                "tools": tools,
                                "description": f"P2P agent {peer_name}",
                            }
                        )
                except Exception as e:
                    logger.warning(f"P2P discovery error: {e}")

            # Add local agent info
            local_agent = {
                "id": getattr(self.agent, "peer_id", "local"),
                "name": getattr(self.agent, "agent_name", "local-agent"),
                "type": "local",
                "tools": await self._get_local_tools(),
                "description": "Local agent with direct tool access",
            }
            agents.append(local_agent)

            logger.debug(f"Discovered {len(agents)} agents for orchestration")
            return agents

        except Exception as e:
            logger.warning(f"P2P agent discovery failed: {e}")
            # Fallback to just local agent
            return [
                {
                    "id": "local",
                    "name": "local-agent",
                    "type": "local",
                    "tools": await self._get_local_tools(),
                    "description": "Local agent (P2P discovery failed)",
                }
            ]

    async def _get_local_tools(self) -> list[dict[str, Any]]:
        """Get locally available tools."""
        try:
            if hasattr(self.agent, "get_available_tools"):
                return self.agent.get_available_tools()
            # Fallback to basic tools
            return [
                {"name": "write_file", "description": "Write content to a file"},
                {"name": "read_file", "description": "Read content from a file"},
                {"name": "list_files", "description": "List files in directory"},
                {
                    "name": "python_analyzer",
                    "description": "Execute Python code in container",
                },
            ]
        except Exception as e:
            logger.warning(f"Failed to get local tools: {e}")
            return []

    async def _get_all_available_tools(
        self, agents: list[dict[str, Any]], local_tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Get all available tools from all agents."""
        all_tools = []

        for agent in agents:
            agent_tools = agent.get("tools", [])
            for tool in agent_tools:
                # Add agent info to tool
                tool_with_agent = tool.copy()
                tool_with_agent["agent_id"] = agent["id"]
                tool_with_agent["agent_name"] = agent["name"]
                tool_with_agent["agent_type"] = agent.get("type", "p2p")
                all_tools.append(tool_with_agent)

        logger.debug(f"Total available tools across all agents: {len(all_tools)}")
        return all_tools

    def _build_agent_context(
        self, agents: list[dict[str, Any]], local_tools: list[dict[str, Any]]
    ) -> str:
        """Build context string for LLM about available agents and tools."""
        context_parts = []

        for agent in agents:
            agent_id = agent.get("id", "unknown")
            agent_name = agent.get("name", "unknown")
            agent_type = agent.get("type", "p2p")
            tools = agent.get("tools", [])

            tool_names = [t.get("name", "unknown") for t in tools]

            context_parts.append(
                f"АГЕНТ: {agent_name} (ID: {agent_id}, TYPE: {agent_type})\n"
                f"Инструменты: {', '.join(tool_names)}\n"
                f"Описание: {agent.get('description', 'Агент в P2P сети')}"
            )

        return "\n\n".join(context_parts)

    def _convert_tools_to_functions(
        self, tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert tools to OpenAI function calling format."""
        functions = []

        for tool in tools:
            # Debug logging
            logger.debug(
                f"Converting tool: {tool.get('name', 'unknown')} - parameters type: {type(tool.get('parameters'))}"
            )
            function_def = {
                "type": "function",
                "function": {
                    "name": tool.get("name", "unknown_tool"),
                    "description": f"{tool.get('description', 'Tool execution')} [Agent: {tool.get('agent_name', 'unknown')}]",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }

            # Add parameters if available
            if "parameters" in tool:
                params = tool["parameters"]

                # If parameters is None or not a dict, keep the default empty schema
                if params is None:
                    # Keep default empty schema - this is valid
                    pass
                elif isinstance(params, dict):
                    # Accept proper JSON Schema as-is; otherwise, convert mapping to JSON Schema
                    if params.get("type") == "object" and isinstance(
                        params.get("properties"), dict
                    ):
                        function_def["function"]["parameters"] = params
                    else:
                        # Convert from flat mapping {name: {type, description, required}} to JSON Schema
                        properties = {}
                        required = []
                        for name, spec in params.items():
                            if isinstance(spec, dict):
                                properties[name] = {
                                    "type": spec.get("type", "string"),
                                    "description": spec.get("description", "Parameter"),
                                }
                                if spec.get("required"):
                                    required.append(name)
                            else:
                                properties[name] = {"type": "string"}
                        function_def["function"]["parameters"]["properties"] = (
                            properties
                        )
                        function_def["function"]["parameters"]["required"] = required
            elif "params" in tool and isinstance(tool["params"], list):
                # Convert from params list format
                properties = {}
                required = []
                for param in tool["params"]:
                    if isinstance(param, dict) and "name" in param:
                        properties[param["name"]] = {
                            "type": param.get("type", "string"),
                            "description": param.get("description", "Parameter"),
                        }
                        if param.get("required"):
                            required.append(param["name"])

                function_def["function"]["parameters"]["properties"] = properties
                function_def["function"]["parameters"]["required"] = required

            functions.append(function_def)

        return functions

    async def _process_llm_orchestration_response(
        self,
        response,
        messages: list[dict],
        agents: list[dict],
        original_command: str = "",
    ) -> dict[str, Any]:
        """Process LLM response and execute tools via P2P."""
        message = response.choices[0].message

        if message.tool_calls:
            logger.info(f"⚡ LLM DECISION: Execute {len(message.tool_calls)} tools")
            for i, tool_call in enumerate(message.tool_calls, 1):
                try:
                    logger.info(
                        f"   🧩 ToolCall[{i}]: name={tool_call.function.name} args={tool_call.function.arguments}"
                    )
                except Exception:
                    pass

            # Add assistant message to conversation
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                        for tool_call in message.tool_calls
                    ],
                }
            )

            # Execute tools via P2P
            tool_results = []
            for i, tool_call in enumerate(message.tool_calls, 1):
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                logger.info(
                    f"🔧 TOOL EXECUTION {i}/{len(message.tool_calls)}: {tool_name}"
                )
                logger.info(f"   📥 Arguments: {tool_args}")

                # Execute tool (local or P2P)
                result = await self._execute_tool_with_p2p(tool_name, tool_args, agents)

                logger.info(
                    f"   📤 Result: {result.get('success', 'unknown')} - {result.get('output', result.get('error', 'no output'))[:100]}"
                )

                tool_results.append(
                    {"tool": tool_name, "arguments": tool_args, "result": result}
                )

                # Add tool result to conversation
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

            # Optional: If natural language indicates 'open' and LLM didn't choose computer-use,
            # try adding a computer_open_app call to remote agent that has it.
            try:
                text = (original_command or "").lower()
                # Augment with computer_use if intent present
                has_open_intent = any(k in text for k in ["открой", "open "])
                chose_computer = any(
                    tr["tool"] == "computer_open_app" for tr in tool_results
                )
                if has_open_intent and not chose_computer:
                    # pick app name heuristically
                    app = None
                    if "finder" in text:
                        app = "Finder"
                    elif "chrome" in text:
                        app = "Google Chrome"
                    if app:
                        # find agent with computer_open_app
                        selected = None
                        for a in agents:
                            for t in a.get("tools", []):
                                if t.get("name") == "computer_open_app":
                                    selected = a
                                    break
                            if selected:
                                break
                        if selected:
                            logger.info(
                                f"🔁 Augmenting with computer_open_app on {selected.get('name')}"
                            )
                            cr = await self._execute_p2p_tool(
                                "computer_open_app", {"app": app}, selected
                            )
                            tool_results.append(
                                {
                                    "tool": "computer_open_app",
                                    "arguments": {"app": app},
                                    "result": cr,
                                }
                            )
                # Augment with telegram_poster if telegram intent present
                has_tg_intent = any(k in text for k in ["телеграм", "telegram"])
                chose_tg = any(tr["tool"] == "telegram_poster" for tr in tool_results)
                if has_tg_intent and not chose_tg:
                    # Log what P2P tools are currently visible for transparency
                    try:
                        if (
                            hasattr(self.agent, "p2p_service")
                            and self.agent.p2p_service
                        ):
                            visible = self.agent.p2p_service.get_all_peer_tools() or {}
                            logger.info(
                                f"P2P visible peer tools: { {k[:8]: [t.get('name') for t in v] for k, v in visible.items()} }"
                            )
                    except Exception as _e:
                        logger.debug(f"Could not list P2P tools: {_e}")
                    selected = None
                    for a in agents:
                        for t in a.get("tools", []):
                            if t.get("name") == "telegram_poster":
                                selected = a
                                break
                        if selected:
                            break
                    # Fallback: if tools list is empty but we have any P2P agent, try first P2P agent by name
                    if not selected:
                        for a in agents:
                            if a.get("type") == "p2p":
                                selected = a
                                break
                    if selected:
                        logger.info(
                            f"🔁 Augmenting with telegram_poster on {selected.get('name')}"
                        )
                        # Extract brief message from text as a fallback
                        msg = original_command.strip()
                        cr = await self._execute_p2p_tool(
                            "telegram_poster", {"message": msg}, selected
                        )
                        tool_results.append(
                            {
                                "tool": "telegram_poster",
                                "arguments": {"message": msg},
                                "result": cr,
                            }
                        )
            except Exception as e:
                logger.debug(f"Augmentation skipped: {e}")

            # Get final LLM response
            final_response = await self.llm_client.chat.completions.create(
                model=self.config.llm.model,
                messages=messages,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens,
            )

            return {
                "success": True,
                "method": "llm_p2p_orchestration",
                "tool_executions": tool_results,
                "response": final_response.choices[0].message.content,
            }
        # No tool calls. If it looks like an 'open app' request, try computer-use via P2P.
        try:
            text = (original_command or "").lower()
            if any(k in text for k in ["открой", "open "]):
                fb = await self._heuristic_fallback(original_command, agents)
                if fb.get("success"):
                    return {
                        "success": True,
                        "method": "heuristic_p2p_computer_use",
                        "result": fb,
                    }
            if any(k in text for k in ["телеграм", "telegram"]):
                # Prefer telegram_poster if available remotely
                selected = None
                for a in agents:
                    for t in a.get("tools", []):
                        if t.get("name") == "telegram_poster":
                            selected = a
                            break
                    if selected:
                        break
                if selected:
                    logger.info(
                        f"Heuristic: selecting agent {selected.get('name')} for telegram_poster"
                    )
                    res = await self._execute_p2p_tool(
                        "telegram_poster",
                        {"message": original_command.strip()},
                        selected,
                    )
                    return {
                        "success": res.get("success", False),
                        "method": "heuristic_p2p_telegram",
                        "result": res,
                    }
        except Exception as e:
            logger.debug(f"Heuristic open-app fallback failed: {e}")
        # Otherwise just return LLM response
        return {
            "success": True,
            "method": "llm_response_only",
            "response": message.content,
        }

    async def _execute_tool_with_p2p(
        self, tool_name: str, arguments: dict[str, Any], agents: list[dict]
    ) -> dict[str, Any]:
        """Execute tool on the best available agent (local or P2P)."""
        logger.info(f"🎯 AGENT SELECTION: Finding best agent for '{tool_name}'")

        # Find which agents have this tool
        candidate_agents = []
        for agent in agents:
            agent_tools = agent.get("tools", [])
            for tool in agent_tools:
                if tool.get("name") == tool_name:
                    candidate_agents.append({"agent": agent, "tool": tool})

        logger.info(
            f"   🔍 Found {len(candidate_agents)} agents with '{tool_name}' tool"
        )

        if not candidate_agents:
            logger.error(f"   ❌ Tool '{tool_name}' not found on any agent")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found on any agent",
            }

        # Select best agent (prefer local, then by type/priority)
        best_candidate = None
        for candidate in candidate_agents:
            if candidate["agent"].get("type") == "local":
                best_candidate = candidate
                break

        if not best_candidate:
            best_candidate = candidate_agents[0]  # First available

        selected_agent = best_candidate["agent"]
        agent_type = selected_agent.get("type", "p2p")
        agent_name = selected_agent.get("name", "unknown")

        logger.info(f"   ✅ Selected: {agent_name} ({agent_type})")

        try:
            if agent_type == "local":
                logger.info(f"🏠 LOCAL EXECUTION: Running '{tool_name}' on local agent")
                return await self._execute_local_tool(tool_name, arguments)
            logger.info(
                f"🌐 P2P EXECUTION: Running '{tool_name}' on remote agent {agent_name}"
            )
            return await self._execute_p2p_tool(tool_name, arguments, selected_agent)

        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "agent": selected_agent.get("name", "unknown"),
            }

    async def _execute_local_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute tool locally."""
        try:
            logger.info(f"   🔄 INVOKING LOCAL TOOL: {tool_name}")
            logger.info(f"   📋 Args: {arguments}")

            if hasattr(self.agent, "invoke_tool"):
                result = await self.agent.invoke_tool(tool_name, arguments)
                logger.info(
                    f"   ✅ LOCAL EXECUTION COMPLETE: {result.get('success', 'unknown')}"
                )
                return result
            # NO FALLBACK - System must have proper invoke_tool method
            error_msg = (
                f"Agent has no invoke_tool method - cannot execute '{tool_name}'"
            )
            logger.error(f"   ❌ CRITICAL ERROR: {error_msg}")
            raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"   ❌ LOCAL EXECUTION FAILED: {e}")
            return {"success": False, "error": str(e), "agent": "local"}

    async def _execute_p2p_tool(
        self, tool_name: str, arguments: dict[str, Any], agent: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute tool on remote agent via P2P."""
        agent_name = agent.get("name", "unknown")
        agent_id = agent.get("id", "unknown")
        logger.info(f"P2P tool execution: {tool_name} on {agent_name} ({agent_id})")
        try:
            if not hasattr(self.agent, "p2p_service") or not self.agent.p2p_service:
                raise RuntimeError("P2P service not available")
            # Prefer name-based convenience if available
            p2p = self.agent.p2p_service
            if agent_name and hasattr(p2p, "call_remote_tool_by_peer_name"):
                result = await p2p.call_remote_tool_by_peer_name(
                    agent_name, tool_name, arguments
                )
            else:
                result = await p2p.invoke_remote_tool(agent_id, tool_name, arguments)
            # Result is already a dict {success, result|error}
            logger.info(f"P2P execution result: success={result.get('success', False)}")
            return result
        except Exception as e:
            logger.error(f"P2P call failed: {e}")
            return {"success": False, "error": str(e), "agent": agent_name}

    async def _heuristic_fallback(
        self, command: str, agents: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Fallback when LLM is unavailable: simple mapping to computer-use tools."""
        text = command.lower()
        app = None
        if "finder" in text:
            app = "Finder"
        elif "chrome" in text:
            app = "Google Chrome"
        elif "safari" in text:
            app = "Safari"
        elif "textedit" in text or "блокнот" in text:
            app = "TextEdit"
        if not app:
            return {"success": False, "error": "No heuristic match for app"}
        # choose agent that has computer_open_app
        selected = None
        for a in agents:
            for t in a.get("tools", []):
                if t.get("name") == "computer_open_app":
                    selected = a
                    break
            if selected:
                break
        if not selected:
            return {
                "success": False,
                "error": "computer-use tool not found on any agent",
            }
        logger.info(
            f"Heuristic: selecting agent {selected.get('name')} for computer_open_app"
        )
        return await self._execute_p2p_tool("computer_open_app", {"app": app}, selected)
