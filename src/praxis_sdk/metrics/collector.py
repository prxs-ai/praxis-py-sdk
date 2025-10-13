"""
Metrics collector for Praxis agents.
Collects and manages Prometheus metrics.
"""

from typing import Dict, Optional, Any
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    CollectorRegistry,
    generate_latest,
)
from loguru import logger


class MetricsCollector:
    """
    Central metrics collector for Praxis agents.

    Manages Prometheus metrics including counters, gauges, and histograms.
    """

    def __init__(
        self,
        agent_name: str,
        environment: str = "development",
        registry: Optional[CollectorRegistry] = None,
        libp2p_peer_id: Optional[str] = None,
    ):
        """
        Initialize metrics collector.

        Args:
            agent_name: Name of the agent
            environment: Environment name (development, production, etc.)
            registry: Prometheus registry (creates new if None)
            libp2p_peer_id: Optional libp2p peer ID to add as label
        """
        self.agent_name = agent_name
        self.environment = environment
        self.libp2p_peer_id = libp2p_peer_id or "unknown"
        self.registry = registry or CollectorRegistry()

        # Storage for metric objects
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}

        # Default labels applied to all metrics
        self._default_labels = {
            "agent_name": agent_name,
            "environment": environment,
            "libp2p_peer_id": self.libp2p_peer_id,
        }

        # Initialize all metrics
        self._init_health_metrics()
        self._init_p2p_metrics()
        self._init_tool_execution_metrics()
        self._init_task_metrics()
        self._init_api_metrics()
        self._init_mcp_metrics()
        self._init_system_metrics()

        logger.debug(
            f"MetricsCollector initialized for agent '{agent_name}' with peer_id '{self.libp2p_peer_id}'"
        )

    def _init_health_metrics(self) -> None:
        """Initialize health check related metrics."""
        # Health check counter
        self._create_counter(
            name="praxis_agent_health_checks_total",
            documentation="Total number of health checks performed",
            labelnames=["status"],
        )

        # Health check response time
        self._create_histogram(
            name="praxis_agent_health_check_duration_seconds",
            documentation="Health check duration in seconds",
            labelnames=[],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0),
        )

        # Agent uptime
        self._create_gauge(
            name="praxis_agent_uptime_seconds",
            documentation="Agent uptime in seconds",
            labelnames=[],
        )

        # Agent info (always 1, used for labels)
        self._create_gauge(
            name="praxis_agent_info",
            documentation="Agent information with labels",
            labelnames=["version", "hostname"],
        )

    def _init_p2p_metrics(self) -> None:
        """Initialize P2P networking metrics."""
        # Connected peers
        self._create_gauge(
            name="praxis_p2p_connected_peers",
            documentation="Number of connected P2P peers",
            labelnames=[],
        )

        # Total connections
        self._create_counter(
            name="praxis_p2p_connections_total",
            documentation="Total P2P connections established",
            labelnames=["direction", "protocol"],
        )

        # Connection errors
        self._create_counter(
            name="praxis_p2p_connection_errors_total",
            documentation="Total P2P connection errors",
            labelnames=["error_type"],
        )

        # Messages sent
        self._create_counter(
            name="praxis_p2p_messages_sent_total",
            documentation="Total P2P messages sent",
            labelnames=["protocol", "message_type"],
        )

        # Messages received
        self._create_counter(
            name="praxis_p2p_messages_received_total",
            documentation="Total P2P messages received",
            labelnames=["protocol", "message_type"],
        )

        # Message size
        self._create_histogram(
            name="praxis_p2p_message_size_bytes",
            documentation="P2P message size in bytes",
            labelnames=["direction", "protocol"],
            buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000),
        )

        # Discovered peers
        self._create_counter(
            name="praxis_p2p_peers_discovered_total",
            documentation="Total peers discovered via mDNS/DHT",
            labelnames=["discovery_method"],
        )

    def _init_tool_execution_metrics(self) -> None:
        """Initialize tool execution metrics."""
        # Tool executions
        self._create_counter(
            name="praxis_tool_executions_total",
            documentation="Total tool executions",
            labelnames=["tool_name", "engine", "status"],
        )

        # Tool execution duration
        self._create_histogram(
            name="praxis_tool_execution_duration_seconds",
            documentation="Tool execution duration in seconds",
            labelnames=["tool_name", "engine"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
        )

        # Active tool executions
        self._create_gauge(
            name="praxis_tool_executions_active",
            documentation="Currently active tool executions",
            labelnames=["tool_name", "engine"],
        )

        # Tool errors
        self._create_counter(
            name="praxis_tool_errors_total",
            documentation="Total tool execution errors",
            labelnames=["tool_name", "engine", "error_type"],
        )

    def _init_task_metrics(self) -> None:
        """Initialize task management metrics."""
        # Tasks received
        self._create_counter(
            name="praxis_tasks_received_total",
            documentation="Total tasks received",
            labelnames=["task_type", "source"],
        )

        # Tasks completed
        self._create_counter(
            name="praxis_tasks_completed_total",
            documentation="Total tasks completed",
            labelnames=["task_type", "status"],
        )

        # Task duration
        self._create_histogram(
            name="praxis_task_duration_seconds",
            documentation="Task execution duration in seconds",
            labelnames=["task_type"],
            buckets=(0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
        )

        # Active tasks
        self._create_gauge(
            name="praxis_tasks_active",
            documentation="Currently active tasks",
            labelnames=["task_type"],
        )

        # Task queue size
        self._create_gauge(
            name="praxis_task_queue_size",
            documentation="Number of tasks in queue",
            labelnames=["queue_name"],
        )

    def _init_api_metrics(self) -> None:
        """Initialize API server metrics."""
        # HTTP requests
        self._create_counter(
            name="praxis_http_requests_total",
            documentation="Total HTTP requests",
            labelnames=["method", "endpoint", "status_code"],
        )

        # HTTP request duration
        self._create_histogram(
            name="praxis_http_request_duration_seconds",
            documentation="HTTP request duration in seconds",
            labelnames=["method", "endpoint"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )

        # WebSocket connections
        self._create_gauge(
            name="praxis_websocket_connections",
            documentation="Active WebSocket connections",
            labelnames=[],
        )

        # WebSocket messages
        self._create_counter(
            name="praxis_websocket_messages_total",
            documentation="Total WebSocket messages",
            labelnames=["direction", "message_type"],
        )

    def _init_mcp_metrics(self) -> None:
        """Initialize MCP (Model Context Protocol) metrics."""
        # MCP tool calls
        self._create_counter(
            name="praxis_mcp_tool_calls_total",
            documentation="Total MCP tool calls",
            labelnames=["server", "tool_name", "status"],
        )

        # MCP tool duration
        self._create_histogram(
            name="praxis_mcp_tool_duration_seconds",
            documentation="MCP tool call duration in seconds",
            labelnames=["server", "tool_name"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        # MCP server status
        self._create_gauge(
            name="praxis_mcp_server_status",
            documentation="MCP server status (1=connected, 0=disconnected)",
            labelnames=["server"],
        )

    def _init_system_metrics(self) -> None:
        """Initialize system resource metrics."""
        # Event bus events
        self._create_counter(
            name="praxis_events_total",
            documentation="Total events published to event bus",
            labelnames=["event_type"],
        )

        # Event processing duration
        self._create_histogram(
            name="praxis_event_processing_duration_seconds",
            documentation="Event processing duration in seconds",
            labelnames=["event_type"],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
        )

        # LLM requests
        self._create_counter(
            name="praxis_llm_requests_total",
            documentation="Total LLM API requests",
            labelnames=["model", "status"],
        )

        # LLM request duration
        self._create_histogram(
            name="praxis_llm_request_duration_seconds",
            documentation="LLM API request duration in seconds",
            labelnames=["model"],
            buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0),
        )

        # LLM tokens
        self._create_counter(
            name="praxis_llm_tokens_total",
            documentation="Total LLM tokens used",
            labelnames=["model", "token_type"],
        )

    def _create_counter(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[list] = None,
    ) -> Counter:
        """Create and register a counter metric."""
        if name in self._counters:
            return self._counters[name]

        # Add default label names
        all_labelnames = list(self._default_labels.keys())
        if labelnames:
            all_labelnames.extend(labelnames)

        counter = Counter(
            name,
            documentation,
            labelnames=all_labelnames,
            registry=self.registry,
        )

        self._counters[name] = counter
        logger.debug(f"Created counter metric: {name}")
        return counter

    def _create_gauge(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[list] = None,
    ) -> Gauge:
        """Create and register a gauge metric."""
        if name in self._gauges:
            return self._gauges[name]

        # Add default label names
        all_labelnames = list(self._default_labels.keys())
        if labelnames:
            all_labelnames.extend(labelnames)

        gauge = Gauge(
            name,
            documentation,
            labelnames=all_labelnames,
            registry=self.registry,
        )

        self._gauges[name] = gauge
        logger.debug(f"Created gauge metric: {name}")
        return gauge

    def _create_histogram(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[list] = None,
        buckets: tuple = (
            0.005,
            0.01,
            0.025,
            0.05,
            0.075,
            0.1,
            0.25,
            0.5,
            0.75,
            1.0,
            2.5,
            5.0,
            7.5,
            10.0,
        ),
    ) -> Histogram:
        """Create and register a histogram metric."""
        if name in self._histograms:
            return self._histograms[name]

        # Add default label names
        all_labelnames = list(self._default_labels.keys())
        if labelnames:
            all_labelnames.extend(labelnames)

        histogram = Histogram(
            name,
            documentation,
            labelnames=all_labelnames,
            buckets=buckets,
            registry=self.registry,
        )

        self._histograms[name] = histogram
        logger.debug(f"Created histogram metric: {name}")
        return histogram

    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Metric name
            value: Value to increment by (default: 1.0)
            labels: Additional labels (beyond default labels)
        """
        if name not in self._counters:
            logger.warning(f"Counter '{name}' not initialized, skipping increment")
            return

        try:
            # Merge default labels with provided labels
            all_labels = {**self._default_labels}
            if labels:
                all_labels.update(labels)

            self._counters[name].labels(**all_labels).inc(value)
        except Exception as e:
            logger.error(f"Failed to increment counter '{name}': {e}")

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Set a gauge metric value.

        Args:
            name: Metric name
            value: Value to set
            labels: Additional labels (beyond default labels)
        """
        if name not in self._gauges:
            logger.warning(f"Gauge '{name}' not initialized, skipping set")
            return

        try:
            # Merge default labels with provided labels
            all_labels = {**self._default_labels}
            if labels:
                all_labels.update(labels)

            self._gauges[name].labels(**all_labels).set(value)
        except Exception as e:
            logger.error(f"Failed to set gauge '{name}': {e}")

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Observe a value in a histogram metric.

        Args:
            name: Metric name
            value: Value to observe
            labels: Additional labels (beyond default labels)
        """
        if name not in self._histograms:
            logger.warning(f"Histogram '{name}' not initialized, skipping observation")
            return

        try:
            # Merge default labels with provided labels
            all_labels = {**self._default_labels}
            if labels:
                all_labels.update(labels)

            self._histograms[name].labels(**all_labels).observe(value)
        except Exception as e:
            logger.error(f"Failed to observe histogram '{name}': {e}")

    def record_health_check(self, status: str, duration: float) -> None:
        """
        Record a health check event.

        Args:
            status: Health check status (healthy, unhealthy, degraded)
            duration: Duration of health check in seconds
        """
        self.increment_counter(
            "praxis_agent_health_checks_total", labels={"status": status}
        )
        self.observe_histogram(
            "praxis_agent_health_check_duration_seconds",
            duration,
        )

    def record_http_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ) -> None:
        """
        Record an HTTP request event.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            status_code: HTTP response status code
            duration: Request duration in seconds
        """
        self.increment_counter(
            "praxis_http_requests_total",
            labels={"method": method, "endpoint": endpoint, "status_code": str(status_code)},
        )
        self.observe_histogram(
            "praxis_http_request_duration_seconds",
            duration,
            labels={"method": method, "endpoint": endpoint},
        )

    def record_task_event(
        self, event_type: str, task_type: str = "generic", source: str = "unknown"
    ) -> None:
        """
        Record a task management event.

        Args:
            event_type: Type of event (received, completed, failed, etc.)
            task_type: Type of task being processed
            source: Source of the task (api, p2p, internal, etc.)
        """
        if event_type == "received":
            self.increment_counter(
                "praxis_tasks_received_total",
                labels={"task_type": task_type, "source": source},
            )
        elif event_type == "completed":
            self.increment_counter(
                "praxis_tasks_completed_total",
                labels={"task_type": task_type, "status": "success"},
            )
        elif event_type == "failed":
            self.increment_counter(
                "praxis_tasks_completed_total",
                labels={"task_type": task_type, "status": "failed"},
            )

    def record_task_duration(self, task_type: str, duration: float) -> None:
        """
        Record task execution duration.

        Args:
            task_type: Type of task
            duration: Task duration in seconds
        """
        self.observe_histogram(
            "praxis_task_duration_seconds",
            duration,
            labels={"task_type": task_type},
        )

    def record_tool_execution(
        self, tool_name: str, engine: str, status: str, duration: float
    ) -> None:
        """
        Record a tool execution event.

        Args:
            tool_name: Name of the tool
            engine: Execution engine used
            status: Execution status (success, failed)
            duration: Execution duration in seconds
        """
        self.increment_counter(
            "praxis_tool_executions_total",
            labels={"tool_name": tool_name, "engine": engine, "status": status},
        )
        self.observe_histogram(
            "praxis_tool_execution_duration_seconds",
            duration,
            labels={"tool_name": tool_name, "engine": engine},
        )

    def record_p2p_message(
        self, direction: str, protocol: str, message_type: str, size_bytes: int = 0
    ) -> None:
        """
        Record a P2P message event.

        Args:
            direction: Message direction (sent, received)
            protocol: P2P protocol used
            message_type: Type of message
            size_bytes: Message size in bytes
        """
        if direction == "sent":
            self.increment_counter(
                "praxis_p2p_messages_sent_total",
                labels={"protocol": protocol, "message_type": message_type},
            )
        elif direction == "received":
            self.increment_counter(
                "praxis_p2p_messages_received_total",
                labels={"protocol": protocol, "message_type": message_type},
            )

        if size_bytes > 0:
            self.observe_histogram(
                "praxis_p2p_message_size_bytes",
                size_bytes,
                labels={"direction": direction, "protocol": protocol},
            )

    def record_websocket_connection(self, connected: bool) -> None:
        """
        Record WebSocket connection change.

        Args:
            connected: True if connecting, False if disconnecting
        """
        current = self._gauges.get("praxis_websocket_connections")
        if current:
            if connected:
                current.labels(**self._default_labels).inc()
            else:
                current.labels(**self._default_labels).dec()

    def record_websocket_message(self, direction: str, message_type: str) -> None:
        """
        Record a WebSocket message event.

        Args:
            direction: Message direction (sent, received)
            message_type: Type of message
        """
        self.increment_counter(
            "praxis_websocket_messages_total",
            labels={"direction": direction, "message_type": message_type},
        )

    def serialize(self) -> bytes:
        """
        Serialize all metrics to Prometheus text format.

        Returns:
            Metrics in Prometheus text format (bytes)
        """
        try:
            return generate_latest(self.registry)
        except Exception as e:
            logger.error(f"Failed to serialize metrics: {e}")
            return b""

    def get_metric_count(self) -> int:
        """Get total number of registered metrics."""
        return len(self._counters) + len(self._gauges) + len(self._histograms)

    def update_libp2p_peer_id(self, peer_id: str) -> None:
        """
        Update the libp2p peer ID after P2P service initialization.

        Args:
            peer_id: The libp2p peer ID
        """
        self.libp2p_peer_id = peer_id
        self._default_labels["libp2p_peer_id"] = peer_id
        logger.info(f"Updated libp2p_peer_id to: {peer_id}")
