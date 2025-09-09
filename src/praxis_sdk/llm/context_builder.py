"""
Context builder for intelligent workflow planning.

This module builds comprehensive network context by gathering information about:
- Available agents and their capabilities
- Available tools and their routing
- Network topology and performance metrics
- Current system load and resource availability
"""

import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from loguru import logger

from ..p2p.service import P2PService
from ..mcp.registry import ToolRegistry
from ..p2p.protocols import AgentCard
from .openai_client import NetworkContext


@dataclass
class AgentCapability:
    """Represents a single agent capability."""
    
    tool_name: str
    description: str
    parameters: Dict[str, Any]
    execution_time_avg: Optional[float] = None
    success_rate: Optional[float] = None


@dataclass
class AgentInfo:
    """Comprehensive information about an agent."""
    
    id: str
    peer_id: str
    capabilities: List[AgentCapability]
    current_load: float
    max_load: float
    location: str
    last_seen: datetime
    response_time_avg: float
    success_rate: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_available(self) -> bool:
        """Check if agent is available for new tasks."""
        return (
            self.current_load < self.max_load * 0.9 and
            (datetime.now() - self.last_seen).seconds < 300  # Seen within 5 minutes
        )
    
    @property
    def load_percentage(self) -> float:
        """Get current load as percentage."""
        return (self.current_load / max(self.max_load, 1)) * 100


@dataclass
class ToolInfo:
    """Information about available tools."""
    
    name: str
    description: str
    parameters: Dict[str, Any]
    available_agents: List[str]
    average_execution_time: float
    success_rate: float
    last_used: Optional[datetime] = None
    usage_count: int = 0


@dataclass
class NetworkMetrics:
    """Network performance and topology metrics."""
    
    total_agents: int
    active_agents: int
    total_tools: int
    average_response_time: float
    network_load: str  # "low", "medium", "high"
    connectivity_score: float  # 0.0 to 1.0
    last_updated: datetime


class NetworkContextBuilder:
    """
    Builds comprehensive network context for intelligent workflow planning.
    
    This class gathers information from various sources:
    - P2P network for agent discovery
    - MCP registry for tool capabilities
    - Performance metrics for optimization
    - Historical data for predictions
    """
    
    def __init__(self, p2p_service: P2PService, mcp_registry: ToolRegistry):
        self.p2p_service = p2p_service
        self.mcp_registry = mcp_registry
        
        # Caches
        self._agent_cache: Dict[str, AgentInfo] = {}
        self._tool_cache: Dict[str, ToolInfo] = {}
        self._metrics_cache: Optional[NetworkMetrics] = None
        self._cache_ttl = 300  # 5 minutes
        self._last_update = datetime.min
        
        # Performance tracking
        self._performance_history: Dict[str, List[float]] = {}
        self._success_history: Dict[str, List[bool]] = {}
    
    async def build_network_context(
        self,
        include_performance_history: bool = True,
        max_age_seconds: int = 300
    ) -> NetworkContext:
        """
        Build comprehensive network context for workflow planning.
        
        Args:
            include_performance_history: Whether to include historical performance data
            max_age_seconds: Maximum age of cached data in seconds
            
        Returns:
            NetworkContext with current network state
        """
        
        try:
            # Check if cache is still valid
            if self._is_cache_valid(max_age_seconds):
                logger.debug("Using cached network context")
                return self._build_context_from_cache()
            
            logger.info("Building fresh network context")
            start_time = datetime.now()
            
            # Gather data concurrently
            tasks = [
                self._discover_agents(),
                self._discover_tools(),
                self._calculate_network_metrics()
            ]
            
            agents, tools, metrics = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions
            if isinstance(agents, Exception):
                logger.error(f"Failed to discover agents: {agents}")
                agents = []
            
            if isinstance(tools, Exception):
                logger.error(f"Failed to discover tools: {tools}")
                tools = []
            
            if isinstance(metrics, Exception):
                logger.error(f"Failed to calculate metrics: {metrics}")
                metrics = NetworkMetrics(
                    total_agents=0,
                    active_agents=0,
                    total_tools=0,
                    average_response_time=1000.0,
                    network_load="unknown",
                    connectivity_score=0.0,
                    last_updated=datetime.now()
                )
            
            # Update caches
            self._update_caches(agents, tools, metrics)
            
            # Build context
            context = NetworkContext(
                available_agents=self._format_agents_for_context(agents),
                available_tools=self._format_tools_for_context(tools),
                network_load=metrics.network_load,
                agent_capabilities=self._build_capability_map(agents),
                tool_routing=self._build_tool_routing(tools)
            )
            
            build_time = (datetime.now() - start_time).total_seconds()
            logger.success(f"Built network context in {build_time:.2f}s: {metrics.active_agents} agents, {len(tools)} tools")
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to build network context: {e}")
            # Return minimal fallback context
            return NetworkContext(
                available_agents=[],
                available_tools=[],
                network_load="unknown",
                agent_capabilities={},
                tool_routing={}
            )
    
    async def get_agent_recommendations(
        self,
        tool_name: str,
        requirements: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get agent recommendations for a specific tool execution.
        
        Args:
            tool_name: Name of the tool to execute
            requirements: Optional requirements (load, location, etc.)
            
        Returns:
            List of recommended agents sorted by suitability
        """
        
        try:
            # Get current context
            context = await self.build_network_context()
            
            # Find agents with the tool
            suitable_agents = []
            for agent_data in context.available_agents:
                if tool_name in agent_data.get("capabilities", []):
                    agent_info = self._agent_cache.get(agent_data["id"])
                    if agent_info and agent_info.is_available:
                        
                        # Calculate suitability score
                        score = self._calculate_agent_suitability(agent_info, tool_name, requirements)
                        
                        suitable_agents.append({
                            **agent_data,
                            "suitability_score": score,
                            "recommendation_reason": self._get_recommendation_reason(agent_info, score)
                        })
            
            # Sort by suitability score
            suitable_agents.sort(key=lambda x: x["suitability_score"], reverse=True)
            
            return suitable_agents
            
        except Exception as e:
            logger.error(f"Failed to get agent recommendations: {e}")
            return []
    
    async def get_network_health(self) -> Dict[str, Any]:
        """
        Get comprehensive network health information.
        
        Returns:
            Network health metrics and status
        """
        
        try:
            context = await self.build_network_context()
            metrics = self._metrics_cache
            
            if not metrics:
                return {"status": "unknown", "reason": "No metrics available"}
            
            # Calculate health scores
            agent_health = min(metrics.active_agents / max(metrics.total_agents, 1), 1.0)
            connectivity_health = metrics.connectivity_score
            performance_health = max(0.0, 1.0 - (metrics.average_response_time / 5000.0))  # 5s = 0 health
            
            overall_health = (agent_health + connectivity_health + performance_health) / 3.0
            
            # Determine status
            if overall_health >= 0.8:
                status = "excellent"
            elif overall_health >= 0.6:
                status = "good"
            elif overall_health >= 0.4:
                status = "fair"
            else:
                status = "poor"
            
            return {
                "status": status,
                "overall_health": overall_health,
                "metrics": {
                    "agent_health": agent_health,
                    "connectivity_health": connectivity_health,
                    "performance_health": performance_health,
                    "active_agents": metrics.active_agents,
                    "total_agents": metrics.total_agents,
                    "average_response_time": metrics.average_response_time,
                    "network_load": metrics.network_load
                },
                "recommendations": self._get_health_recommendations(overall_health, metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to get network health: {e}")
            return {
                "status": "error",
                "reason": str(e),
                "overall_health": 0.0
            }
    
    async def _discover_agents(self) -> List[AgentInfo]:
        """Discover available agents through P2P network."""
        try:
            agents = []
            
            # Get peers from P2P service
            peer_cards = await self.p2p_service.get_all_agent_cards()
            
            for peer_id, card_data in peer_cards.items():
                try:
                    # Parse agent card
                    agent_card = AgentCard(**card_data)
                    
                    # Build capabilities list
                    capabilities = []
                    for tool_name, tool_info in agent_card.capabilities.items():
                        capabilities.append(AgentCapability(
                            tool_name=tool_name,
                            description=tool_info.get("description", ""),
                            parameters=tool_info.get("parameters", {}),
                            execution_time_avg=self._get_avg_execution_time(peer_id, tool_name),
                            success_rate=self._get_tool_success_rate(peer_id, tool_name)
                        ))
                    
                    # Create agent info
                    agent_info = AgentInfo(
                        id=agent_card.id,
                        peer_id=peer_id,
                        capabilities=capabilities,
                        current_load=agent_card.load.get("current", 0.0),
                        max_load=agent_card.load.get("max", 1.0),
                        location=agent_card.location,
                        last_seen=datetime.now(),  # Could be more accurate
                        response_time_avg=self._get_avg_response_time(peer_id),
                        success_rate=self._get_agent_success_rate(peer_id),
                        metadata=agent_card.metadata
                    )
                    
                    agents.append(agent_info)
                    
                except Exception as e:
                    logger.warning(f"Failed to process agent card for {peer_id}: {e}")
                    continue
            
            return agents
            
        except Exception as e:
            logger.error(f"Failed to discover agents: {e}")
            return []
    
    async def _discover_tools(self) -> List[ToolInfo]:
        """Discover available tools through MCP registry."""
        try:
            tools = []
            
            # Get tools from MCP registry
            discovered_tools = await self.mcp_registry.discover_all_tools()
            
            for server_name, tool_list in discovered_tools.items():
                for tool in tool_list:
                    tool_name = tool.get("name", "unknown")
                    
                    # Find which agents have this tool
                    available_agents = []
                    for agent_info in self._agent_cache.values():
                        for capability in agent_info.capabilities:
                            if capability.tool_name == tool_name:
                                available_agents.append(agent_info.id)
                                break
                    
                    # Create tool info
                    tool_info = ToolInfo(
                        name=tool_name,
                        description=tool.get("description", ""),
                        parameters=tool.get("inputSchema", {}).get("properties", {}),
                        available_agents=available_agents,
                        average_execution_time=self._get_tool_avg_execution_time(tool_name),
                        success_rate=self._get_tool_overall_success_rate(tool_name),
                        usage_count=self._get_tool_usage_count(tool_name)
                    )
                    
                    tools.append(tool_info)
            
            return tools
            
        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
            return []
    
    async def _calculate_network_metrics(self) -> NetworkMetrics:
        """Calculate network performance and topology metrics."""
        try:
            # Count agents and tools
            total_agents = len(self._agent_cache)
            active_agents = sum(1 for agent in self._agent_cache.values() if agent.is_available)
            total_tools = len(self._tool_cache)
            
            # Calculate average response time
            if self._agent_cache:
                avg_response_time = sum(agent.response_time_avg for agent in self._agent_cache.values()) / len(self._agent_cache)
            else:
                avg_response_time = 1000.0  # Default to 1 second
            
            # Determine network load
            if active_agents == 0:
                network_load = "no_agents"
            else:
                avg_load = sum(agent.load_percentage for agent in self._agent_cache.values()) / len(self._agent_cache)
                if avg_load < 30:
                    network_load = "low"
                elif avg_load < 70:
                    network_load = "medium"
                else:
                    network_load = "high"
            
            # Calculate connectivity score
            if total_agents == 0:
                connectivity_score = 0.0
            else:
                connectivity_score = active_agents / total_agents
            
            return NetworkMetrics(
                total_agents=total_agents,
                active_agents=active_agents,
                total_tools=total_tools,
                average_response_time=avg_response_time,
                network_load=network_load,
                connectivity_score=connectivity_score,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate network metrics: {e}")
            return NetworkMetrics(
                total_agents=0,
                active_agents=0,
                total_tools=0,
                average_response_time=1000.0,
                network_load="unknown",
                connectivity_score=0.0,
                last_updated=datetime.now()
            )
    
    def _is_cache_valid(self, max_age_seconds: int) -> bool:
        """Check if cached data is still valid."""
        return (datetime.now() - self._last_update).seconds < max_age_seconds
    
    def _build_context_from_cache(self) -> NetworkContext:
        """Build network context from cached data."""
        return NetworkContext(
            available_agents=self._format_agents_for_context(list(self._agent_cache.values())),
            available_tools=self._format_tools_for_context(list(self._tool_cache.values())),
            network_load=self._metrics_cache.network_load if self._metrics_cache else "unknown",
            agent_capabilities=self._build_capability_map(list(self._agent_cache.values())),
            tool_routing=self._build_tool_routing(list(self._tool_cache.values()))
        )
    
    def _update_caches(self, agents: List[AgentInfo], tools: List[ToolInfo], metrics: NetworkMetrics):
        """Update internal caches with fresh data."""
        self._agent_cache = {agent.id: agent for agent in agents}
        self._tool_cache = {tool.name: tool for tool in tools}
        self._metrics_cache = metrics
        self._last_update = datetime.now()
    
    def _format_agents_for_context(self, agents: List[AgentInfo]) -> List[Dict[str, Any]]:
        """Format agents for NetworkContext."""
        return [
            {
                "id": agent.id,
                "peer_id": agent.peer_id,
                "capabilities": [cap.tool_name for cap in agent.capabilities],
                "load": agent.load_percentage,
                "status": "available" if agent.is_available else "busy",
                "location": agent.location,
                "response_time": agent.response_time_avg
            }
            for agent in agents
        ]
    
    def _format_tools_for_context(self, tools: List[ToolInfo]) -> List[Dict[str, Any]]:
        """Format tools for NetworkContext."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "available_agents": tool.available_agents,
                "execution_time": tool.average_execution_time,
                "success_rate": tool.success_rate
            }
            for tool in tools
        ]
    
    def _build_capability_map(self, agents: List[AgentInfo]) -> Dict[str, List[str]]:
        """Build mapping of agents to their capabilities."""
        capability_map = {}
        for agent in agents:
            capability_map[agent.id] = [cap.tool_name for cap in agent.capabilities]
        return capability_map
    
    def _build_tool_routing(self, tools: List[ToolInfo]) -> Dict[str, List[str]]:
        """Build mapping of tools to available agents."""
        routing_map = {}
        for tool in tools:
            routing_map[tool.name] = tool.available_agents
        return routing_map
    
    def _calculate_agent_suitability(
        self,
        agent_info: AgentInfo,
        tool_name: str,
        requirements: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate suitability score for an agent."""
        score = 1.0
        
        # Factor in current load (lower is better)
        load_factor = 1.0 - (agent_info.load_percentage / 100.0)
        score *= (0.3 + 0.7 * load_factor)  # Load weighted at 70%
        
        # Factor in success rate
        score *= agent_info.success_rate
        
        # Factor in response time (lower is better)
        response_factor = max(0.1, 1.0 - (agent_info.response_time_avg / 5000.0))
        score *= response_factor
        
        # Apply requirements if specified
        if requirements:
            if "max_load" in requirements and agent_info.load_percentage > requirements["max_load"]:
                score *= 0.5
            
            if "preferred_location" in requirements:
                if agent_info.location == requirements["preferred_location"]:
                    score *= 1.2
                else:
                    score *= 0.8
        
        return min(score, 1.0)
    
    def _get_recommendation_reason(self, agent_info: AgentInfo, score: float) -> str:
        """Generate recommendation reason for an agent."""
        reasons = []
        
        if agent_info.load_percentage < 30:
            reasons.append("low load")
        
        if agent_info.success_rate > 0.9:
            reasons.append("high success rate")
        
        if agent_info.response_time_avg < 1000:
            reasons.append("fast response")
        
        if score > 0.8:
            return f"Excellent choice: {', '.join(reasons)}"
        elif score > 0.6:
            return f"Good choice: {', '.join(reasons)}"
        else:
            return f"Available but not optimal: {', '.join(reasons) if reasons else 'no specific advantages'}"
    
    def _get_health_recommendations(self, health_score: float, metrics: NetworkMetrics) -> List[str]:
        """Generate health improvement recommendations."""
        recommendations = []
        
        if health_score < 0.5:
            recommendations.append("Consider adding more agents to the network")
        
        if metrics.average_response_time > 3000:
            recommendations.append("High response times detected - check network connectivity")
        
        if metrics.active_agents / max(metrics.total_agents, 1) < 0.7:
            recommendations.append("Many agents are offline - verify agent health")
        
        if metrics.network_load == "high":
            recommendations.append("Network load is high - consider load balancing")
        
        return recommendations
    
    # Helper methods for performance tracking (simplified for now)
    def _get_avg_execution_time(self, peer_id: str, tool_name: str) -> float:
        """Get average execution time for a tool on an agent."""
        key = f"{peer_id}:{tool_name}"
        history = self._performance_history.get(key, [2.0])  # Default 2 seconds
        return sum(history) / len(history)
    
    def _get_tool_success_rate(self, peer_id: str, tool_name: str) -> float:
        """Get success rate for a tool on an agent."""
        key = f"{peer_id}:{tool_name}"
        history = self._success_history.get(key, [True])  # Default success
        return sum(history) / len(history)
    
    def _get_avg_response_time(self, peer_id: str) -> float:
        """Get average response time for an agent."""
        return 1000.0  # Default 1 second - could be tracked
    
    def _get_agent_success_rate(self, peer_id: str) -> float:
        """Get overall success rate for an agent."""
        return 0.95  # Default 95% - could be tracked
    
    def _get_tool_avg_execution_time(self, tool_name: str) -> float:
        """Get average execution time across all agents for a tool."""
        return 2.0  # Default 2 seconds
    
    def _get_tool_overall_success_rate(self, tool_name: str) -> float:
        """Get overall success rate for a tool."""
        return 0.9  # Default 90%
    
    def _get_tool_usage_count(self, tool_name: str) -> int:
        """Get usage count for a tool."""
        return 0  # Default 0 - could be tracked