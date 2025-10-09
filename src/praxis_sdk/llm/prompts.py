"""LLM prompt templates for workflow planning and agent interaction."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PromptTemplate:
    """Container for LLM prompt templates."""

    system_prompt: str
    user_template: str
    examples: list[dict[str, str]]
    context_fields: list[str]


class WorkflowPrompts:
    """Prompt templates for workflow generation and planning."""

    WORKFLOW_GENERATION = PromptTemplate(
        system_prompt="""You are an intelligent workflow planner for a distributed agent network. Your task is to convert natural language requests into executable DSL (Domain Specific Language) workflows.

AVAILABLE DSL SYNTAX:
- Basic commands: `tool_name arg1 arg2 "arg with spaces"`
- Sequential execution: Commands separated by newlines
- Comments: Lines starting with #

AGENT CAPABILITIES:
{available_agents}

AVAILABLE TOOLS:
{available_tools}

RULES:
1. Always use available tools and agents from the provided context
2. Generate simple, executable DSL commands
3. If a tool is not available, suggest alternatives or indicate unavailability
4. Consider agent capabilities when routing tasks
5. Keep workflows simple and linear for now (no parallel execution)
6. Use proper argument quoting for strings with spaces

RESPONSE FORMAT:
Generate a JSON response with:
- "dsl": The executable DSL workflow
- "description": Brief explanation of what the workflow does
- "agents_used": List of agents that will be involved
- "estimated_time": Rough estimate in minutes
""",
        user_template="""Please convert this natural language request into an executable DSL workflow:

REQUEST: {user_request}

NETWORK CONTEXT:
- Available Agents: {agent_count}
- Available Tools: {tool_count}
- Current Load: {network_load}

Generate the DSL workflow that best fulfills this request.""",
        examples=[
            {
                "input": "Analyze recent tweets about Tesla and create a summary report",
                "output": """{"dsl": "scrape_twitter 'Tesla' --count 100\\nextract_sentiment\\ngenerate_report --format markdown", "description": "Scrapes recent Tesla tweets, analyzes sentiment, and generates a markdown report", "agents_used": ["scraper-agent", "analysis-agent"], "estimated_time": 5}""",
            },
            {
                "input": "Check disk space and send notification if low",
                "output": """{"dsl": "check_disk_space\\nif_low_space send_notification 'Disk space is low'", "description": "Monitors disk space and sends notification if below threshold", "agents_used": ["system-agent"], "estimated_time": 1}""",
            },
        ],
        context_fields=[
            "available_agents",
            "available_tools",
            "user_request",
            "agent_count",
            "tool_count",
            "network_load",
        ],
    )

    AGENT_SELECTION = PromptTemplate(
        system_prompt="""You are an intelligent agent selector for a distributed system. Your task is to determine which agent is best suited for executing a specific tool or task.

SELECTION CRITERIA:
1. Agent must have the required tool available
2. Consider agent current load and availability
3. Prefer agents with better performance for the task type
4. Consider network locality and latency

AGENT INFORMATION:
{agent_details}

RESPONSE FORMAT:
Return JSON with:
- "selected_agent": The best agent ID for the task
- "reason": Brief explanation of why this agent was chosen
- "alternatives": List of other viable agents (if any)
- "confidence": Confidence score (0-1)
""",
        user_template="""Select the best agent to execute this tool:

TOOL: {tool_name}
ARGUMENTS: {tool_args}
PRIORITY: {task_priority}

Consider agent capabilities, current load, and network conditions.""",
        examples=[
            {
                "input": "tool: file_operations, priority: high",
                "output": """{"selected_agent": "filesystem-agent-1", "reason": "Has exclusive file operations capability and low current load", "alternatives": ["filesystem-agent-2"], "confidence": 0.95}""",
            }
        ],
        context_fields=["agent_details", "tool_name", "tool_args", "task_priority"],
    )

    PLAN_OPTIMIZATION = PromptTemplate(
        system_prompt="""You are a workflow optimization specialist. Your task is to analyze and optimize DSL workflows for better performance, reliability, and resource utilization.

OPTIMIZATION GOALS:
1. Minimize execution time
2. Optimize resource usage
3. Improve error resilience
4. Reduce network overhead
5. Ensure proper task ordering

CURRENT NETWORK STATE:
{network_state}

RESPONSE FORMAT:
Return JSON with:
- "optimized_dsl": The optimized DSL workflow
- "changes_made": List of optimizations applied
- "performance_impact": Expected performance improvement
- "risks": Potential risks or trade-offs
""",
        user_template="""Please optimize this DSL workflow:

ORIGINAL DSL:
{original_dsl}

CONSTRAINTS:
- Maximum execution time: {max_execution_time} minutes
- Available resources: {available_resources}
- Error tolerance: {error_tolerance}

Optimize for: {optimization_goal}""",
        examples=[
            {
                "input": "file_read large_file.txt\nprocess_data\nfile_write output.txt",
                "output": """{"optimized_dsl": "file_stream large_file.txt | process_data --streaming | file_write output.txt", "changes_made": ["Added streaming to reduce memory usage"], "performance_impact": "50% reduction in memory usage", "risks": ["Streaming may be slower for small files"]}""",
            }
        ],
        context_fields=[
            "network_state",
            "original_dsl",
            "max_execution_time",
            "available_resources",
            "error_tolerance",
            "optimization_goal",
        ],
    )

    CONTEXT_UNDERSTANDING = PromptTemplate(
        system_prompt="""You are a context analyzer for workflow planning. Your task is to understand the user's intent and extract relevant context information to improve workflow generation.

CONTEXT ANALYSIS GOALS:
1. Extract key entities and requirements
2. Identify data sources and targets
3. Determine urgency and priority
4. Understand success criteria
5. Identify potential constraints

RESPONSE FORMAT:
Return JSON with:
- "intent": Primary user intent
- "entities": Key entities mentioned
- "requirements": Functional requirements
- "constraints": Technical or business constraints
- "success_criteria": How to measure success
- "priority": Task priority (low/medium/high)
""",
        user_template="""Analyze this user request to extract context for workflow planning:

REQUEST: {user_request}

CURRENT CONTEXT:
- Time: {current_time}
- User role: {user_role}
- System state: {system_state}

Extract all relevant context information.""",
        examples=[
            {
                "input": "I need to backup all important files before the server maintenance tonight",
                "output": """{"intent": "data_backup", "entities": ["important files", "server"], "requirements": ["identify important files", "create backup", "complete before maintenance"], "constraints": ["time-sensitive", "maintenance window"], "success_criteria": ["all important files backed up", "backup verified"], "priority": "high"}""",
            }
        ],
        context_fields=["user_request", "current_time", "user_role", "system_state"],
    )


class ErrorRecoveryPrompts:
    """Prompt templates for error recovery and troubleshooting."""

    ERROR_ANALYSIS = PromptTemplate(
        system_prompt="""You are an error analysis specialist. Your task is to analyze workflow execution errors and suggest recovery strategies.

ERROR ANALYSIS GOALS:
1. Identify root cause of failures
2. Suggest recovery strategies
3. Recommend workflow modifications
4. Prevent similar errors in future

RESPONSE FORMAT:
Return JSON with:
- "root_cause": Primary cause of the error
- "recovery_strategy": Recommended recovery approach
- "workflow_modifications": Suggested changes to prevent recurrence
- "retry_feasible": Whether retry is recommended
- "alternative_approach": Alternative workflow if recovery fails
""",
        user_template="""Analyze this workflow execution error:

ERROR: {error_message}
WORKFLOW: {failed_workflow}
EXECUTION_CONTEXT: {execution_context}
SYSTEM_STATE: {system_state}

Provide analysis and recovery recommendations.""",
        examples=[
            {
                "input": "Error: Tool 'process_data' not found on agent-2",
                "output": """{"root_cause": "tool_availability", "recovery_strategy": "retry_on_different_agent", "workflow_modifications": ["add agent capability check before execution"], "retry_feasible": true, "alternative_approach": "use local processing tool instead"}""",
            }
        ],
        context_fields=[
            "error_message",
            "failed_workflow",
            "execution_context",
            "system_state",
        ],
    )


def format_prompt(template: PromptTemplate, context: dict[str, Any]) -> dict[str, str]:
    """Format a prompt template with provided context.

    Args:
        template: The prompt template to format
        context: Context dictionary with values for template variables

    Returns:
        Dictionary with formatted system_prompt and user_prompt

    """
    # Check for missing required context fields
    missing_fields = [
        field for field in template.context_fields if field not in context
    ]
    if missing_fields:
        raise ValueError(f"Missing required context fields: {missing_fields}")

    # Format system prompt
    formatted_system = template.system_prompt.format(**context)

    # Format user prompt
    formatted_user = template.user_template.format(**context)

    return {
        "system_prompt": formatted_system,
        "user_prompt": formatted_user,
        "examples": template.examples,
    }


def get_workflow_generation_prompt(
    user_request: str,
    available_agents: list[dict[str, Any]],
    available_tools: list[dict[str, Any]],
    network_context: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Generate a formatted prompt for workflow generation.

    Args:
        user_request: The user's natural language request
        available_agents: List of available agents with their capabilities
        available_tools: List of available tools
        network_context: Optional network state information

    Returns:
        Formatted prompt dictionary

    """
    # Format agents list
    agents_text = "\n".join(
        [
            f"- {agent.get('id', 'unknown')}: {', '.join(agent.get('capabilities', []))}"
            for agent in available_agents
        ]
    )

    # Format tools list
    tools_text = "\n".join(
        [
            f"- {tool.get('name', 'unknown')}: {tool.get('description', 'No description')}"
            for tool in available_tools
        ]
    )

    # Default network context
    if network_context is None:
        network_context = {
            "agent_count": len(available_agents),
            "tool_count": len(available_tools),
            "network_load": "normal",
        }

    context = {
        "user_request": user_request,
        "available_agents": agents_text,
        "available_tools": tools_text,
        "agent_count": network_context.get("agent_count", len(available_agents)),
        "tool_count": network_context.get("tool_count", len(available_tools)),
        "network_load": network_context.get("network_load", "normal"),
    }

    return format_prompt(WorkflowPrompts.WORKFLOW_GENERATION, context)
