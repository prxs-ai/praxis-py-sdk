# Health Monitoring API



## Table of Contents
1. [Introduction](#introduction)
2. [Health Check Endpoint](#health-check-endpoint)
3. [Statistics Endpoint](#statistics-endpoint)
4. [Integration with Monitoring Tools](#integration-with-monitoring-tools)
5. [Debugging and Diagnostics](#debugging-and-diagnostics)
6. [Custom Health Checks](#custom-health-checks)
7. [Code Examples](#code-examples)
8. [Conclusion](#conclusion)

## Introduction
The Health Monitoring API provides essential endpoints for monitoring the operational status and performance of the Praxis Agent system. This document details the `/health` and `/stats` endpoints, their response formats, and integration with container orchestration, load balancing, and external monitoring tools. The API enables system administrators and developers to ensure service reliability, diagnose issues, and maintain optimal performance.

## Health Check Endpoint

The `/health` endpoint provides a simple, standardized way to check the operational status of the Praxis Agent. It is designed for integration with container orchestration platforms like Kubernetes and load balancers to determine service availability.

### Response Format
The health check returns a JSON object with the following structure:

```json
{
  "status": "healthy",
  "agent": "praxis-agent",
  "version": "1.0.0",
  "timestamp": "2023-12-07T10:30:00Z",
  "uptime_seconds": 0.0,
  "config": {
    "p2p_enabled": true,
    "llm_enabled": true,
    "tools_available": 5,
    "active_tasks": 2
  }
}
```

**Key fields:**
- `status`: Current health status ("healthy" or "error")
- `agent`: Name of the agent instance
- `version`: API version
- `timestamp`: UTC timestamp of the check
- `uptime_seconds`: Duration the service has been running
- `config`: Configuration details including P2P, LLM, tools, and active tasks

### Usage in Container Orchestration
Container platforms can use the `/health` endpoint to:
- Determine if a container is ready to receive traffic (readiness probe)
- Verify if a container is still functioning properly (liveness probe)
- Trigger automatic restarts when health checks fail

**Example Kubernetes configuration:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

**Section sources**
- [handlers.py](file://src/praxis_sdk/api/handlers.py#L27-L64)

## Statistics Endpoint

The `/stats` endpoint provides comprehensive metrics from various components of the Praxis system, enabling detailed performance monitoring and system diagnostics.

### Response Structure
The statistics endpoint returns a JSON object containing metrics from multiple system components:

```json
{
  "api_gateway": {
    "active_websockets": 3,
    "total_tasks": 15,
    "available_tools": 8,
    "task_states": {
      "submitted": 2,
      "working": 3,
      "completed": 8,
      "failed": 1,
      "cancelled": 1
    }
  },
  "get_request_handlers()": {
    "total_requests": 125,
    "successful_requests": 120,
    "failed_requests": 5,
    "dsl_commands": 45,
    "jsonrpc_requests": 80,
    "tool_invocations": 32,
    "task_creations": 15,
    "success_rate": 0.96,
    "error_rate": 0.04
  },
  "websocket_manager": {
    "total_connections": 25,
    "active_connections": 3,
    "messages_sent": 156,
    "messages_received": 89,
    "broadcast_count": 45,
    "errors": 2
  },
  "event_bus": {
    "events_published": 250,
    "events_processed": 248,
    "handler_errors": 1,
    "active_handlers": 12,
    "websocket_connections": 3,
    "running": true
  },
  "server": {
    "running": true,
    "config": {
      "environment": "development",
      "api_host": "0.0.0.0",
      "api_port": 8000,
      "websocket_enabled": true,
      "p2p_enabled": true
    }
  }
}
```

### Component-Specific Metrics

#### API Gateway
- `active_websockets`: Number of currently connected WebSocket clients
- `total_tasks`: Total number of tasks managed by the gateway
- `available_tools`: Number of tools accessible through the API
- `task_states`: Breakdown of tasks by their current state

#### Request Handlers
- `total_requests`: Total HTTP requests processed
- `successful_requests`: Successfully processed requests
- `failed_requests`: Failed requests
- `dsl_commands`: Legacy DSL commands executed
- `jsonrpc_requests`: A2A JSON-RPC requests processed
- `tool_invocations`: Number of tool invocations
- `task_creations`: Tasks created
- `success_rate`: Percentage of successful requests
- `error_rate`: Percentage of failed requests

#### WebSocket Manager
- `total_connections`: Total WebSocket connections established
- `active_connections`: Currently active WebSocket connections
- `messages_sent`: Messages sent to clients
- `messages_received`: Messages received from clients
- `broadcast_count`: Broadcast messages sent
- `errors`: WebSocket-related errors

#### Event Bus
- `events_published`: Events published to the bus
- `events_processed`: Events successfully processed
- `handler_errors`: Errors in event handlers
- `active_handlers`: Active event subscribers
- `websocket_connections`: WebSocket connections receiving events

#### Server Configuration
- `running`: Server operational status
- `config`: Server configuration including environment, host, port, and feature flags

```mermaid
graph TD
A[/stats Endpoint] --> B[API Gateway]
A --> C[Request Handlers]
A --> D[WebSocket Manager]
A --> E[Event Bus]
A --> F[Server Configuration]
B --> B1[Active WebSockets]
B --> B2[Total Tasks]
B --> B3[Available Tools]
C --> C1[Total Requests]
C --> C2[Success/Failure Rates]
C --> C3[Command Types]
D --> D1[Connections]
D --> D2[Messages]
E --> E1[Events]
E --> E2[Handlers]
F --> F1[Environment]
F --> F2[Network Settings]
```

**Diagram sources**
- [server.py](file://src/praxis_sdk/api/server.py#L427-L460)
- [gateway.py](file://src/praxis_sdk/api/gateway.py#L529-L547)
- [websocket.py](file://src/praxis_sdk/api/websocket.py)
- [bus.py](file://src/praxis_sdk/bus.py)

**Section sources**
- [server.py](file://src/praxis_sdk/api/server.py#L427-L460)

## Integration with Monitoring Tools

The Health Monitoring API can be integrated with popular monitoring and visualization tools to provide comprehensive system observability.

### Prometheus Integration
Prometheus can scrape metrics from the `/stats` endpoint using a custom exporter or by configuring a metrics endpoint.

**Example Python exporter:**
```python
from prometheus_client import start_http_server, Gauge
import requests
import time

# Define Prometheus metrics
ACTIVE_WEBSOCKETS = Gauge('praxis_active_websockets', 'Number of active WebSocket connections')
TOTAL_REQUESTS = Gauge('praxis_total_requests', 'Total HTTP requests processed')
SUCCESS_RATE = Gauge('praxis_success_rate', 'Request success rate')

def collect_metrics():
    try:
        response = requests.get('http://localhost:8000/stats')
        stats = response.json()
        
        # Update Prometheus metrics
        ACTIVE_WEBSOCKETS.set(stats['websocket_manager']['active_connections'])
        TOTAL_REQUESTS.set(stats['get_request_handlers()']['total_requests'])
        SUCCESS_RATE.set(stats['get_request_handlers()']['success_rate'])
        
    except Exception as e:
        print(f"Error collecting metrics: {e}")

if __name__ == '__main__':
    # Start Prometheus metrics server
    start_http_server(8001)
    
    # Collect metrics every 15 seconds
    while True:
        collect_metrics()
        time.sleep(15)
```

### Grafana Dashboard
Grafana can visualize the collected metrics with dashboards showing:

- System health status over time
- Request volume and success rates
- Active WebSocket connections
- Task processing performance
- Resource utilization trends

**Recommended dashboard panels:**
- Health status indicator (green/yellow/red)
- Requests per second graph
- Error rate percentage
- Active connections gauge
- Task state distribution (pie chart)
- Response time percentiles

## Debugging and Diagnostics

The statistics endpoint provides valuable information for diagnosing performance issues and system problems.

### Performance Issue Diagnosis
When experiencing performance issues, examine the following metrics:

**High Error Rates**
- Check `failed_requests` and `handler_errors`
- Monitor `error_rate` trend over time
- Investigate specific error types in application logs

**Slow Response Times**
- Analyze task processing times
- Check for bottlenecks in specific components
- Monitor WebSocket message processing

**Resource Exhaustion**
- Watch `active_websockets` for connection leaks
- Monitor `total_tasks` for task accumulation
- Check memory usage if available

### Common Issues and Solutions

**Issue: High number of failed requests**
- **Possible causes:** Configuration errors, resource constraints, network issues
- **Diagnostic steps:** Check error logs, verify configuration, monitor system resources
- **Solutions:** Fix configuration, scale resources, improve network connectivity

**Issue: WebSocket connection drops**
- **Possible causes:** Network instability, server overload, client issues
- **Diagnostic steps:** Check `websocket_manager` metrics, examine connection patterns
- **Solutions:** Optimize network, implement reconnection logic, scale server

**Issue: Task processing delays**
- **Possible causes:** Resource contention, inefficient workflows, external dependencies
- **Diagnostic steps:** Analyze task state distribution, check processing times
- **Solutions:** Optimize workflows, add resources, improve external service integration

## Custom Health Checks

The Health Monitoring API supports custom health checks for specific use cases and requirements.

### Implementing Custom Health Checks
Custom health checks can be implemented by extending the existing health check functionality:

```python
async def custom_health_check():
    """Custom health check with additional validations."""
    base_health = await handle_health_check()
    
    # Add custom validations
    custom_checks = {
        "database_connection": check_database(),
        "external_api": check_external_api(),
        "disk_space": check_disk_space(),
        "memory_usage": check_memory_usage()
    }
    
    # Update status based on custom checks
    if not all(custom_checks.values()):
        base_health["status"] = "degraded"
    
    base_health["custom_checks"] = custom_checks
    return base_health
```

### Health Check Levels
The system supports multiple health levels:

- **Healthy:** All systems operational
- **Degraded:** Some non-critical systems affected
- **Unhealthy:** Critical systems failing
- **Maintenance:** System under maintenance

### Alerting Configuration
Configure alerts based on health check results:

```yaml
# Example alert configuration
alerts:
  - name: "Service Down"
    condition: "status != 'healthy'"
    severity: "critical"
    duration: "5m"
    notification: "pagerduty"
  
  - name: "High Error Rate"
    condition: "error_rate > 0.1"
    severity: "warning"
    duration: "10m"
    notification: "email"
  
  - name: "Connection Leak"
    condition: "active_websockets > 100"
    severity: "warning"
    duration: "15m"
    notification: "slack"
```

## Code Examples

### curl Examples

**Health check:**
```bash
curl -X GET http://localhost:8000/health
```

**Statistics endpoint:**
```bash
curl -X GET http://localhost:8000/stats
```

**Formatted output:**
```bash
curl -X GET http://localhost:8000/stats | python -m json.tool
```

**Monitor health continuously:**
```bash
watch -n 5 'curl -s http://localhost:8000/health | grep status'
```

### Python Examples

**Basic health check:**
```python
import requests
import json

def check_health():
    response = requests.get('http://localhost:8000/health')
    health_data = response.json()
    
    print(f"Status: {health_data['status']}")
    print(f"Agent: {health_data['agent']}")
    print(f"Version: {health_data['version']}")
    
    return health_data['status'] == 'healthy'

# Usage
if check_health():
    print("Service is healthy")
else:
    print("Service is unhealthy")
```

**Comprehensive statistics analysis:**
```python
import requests
import json
from datetime import datetime

def analyze_statistics():
    """Analyze system statistics and provide insights."""
    try:
        response = requests.get('http://localhost:8000/stats')
        stats = response.json()
        
        print(f"Analysis at: {datetime.now()}")
        print("=" * 50)
        
        # API Gateway analysis
        gateway = stats['api_gateway']
        print(f"Active WebSockets: {gateway['active_websockets']}")
        print(f"Total Tasks: {gateway['total_tasks']}")
        print(f"Available Tools: {gateway['available_tools']}")
        
        # Request handlers analysis
        handlers = stats['get_request_handlers()']
        print(f"Total Requests: {handlers['total_requests']}")
        print(f"Success Rate: {handlers['success_rate']:.2%}")
        print(f"Error Rate: {handlers['error_rate']:.2%}")
        
        # WebSocket manager analysis
        websocket = stats['websocket_manager']
        print(f"Active Connections: {websocket['active_connections']}")
        print(f"Messages Sent: {websocket['messages_sent']}")
        
        # Event bus analysis
        event_bus = stats['event_bus']
        print(f"Events Processed: {event_bus['events_processed']}")
        print(f"Handler Errors: {event_bus['handler_errors']}")
        
        return stats
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}")
        return None

# Usage
statistics = analyze_statistics()
if statistics:
    print("Analysis complete")
```

**Monitoring script:**
```python
import requests
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class HealthMonitor:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.health_url = f"{base_url}/health"
        self.stats_url = f"{base_url}/stats"
    
    def monitor(self, interval=30):
        """Monitor system health at regular intervals."""
        logging.info(f"Starting health monitor for {self.base_url}")
        
        while True:
            try:
                # Check health
                health_response = requests.get(self.health_url, timeout=10)
                health_data = health_response.json()
                
                # Get statistics
                stats_response = requests.get(self.stats_url, timeout=10)
                stats_data = stats_response.json()
                
                # Log results
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logging.info(f"{timestamp} - Status: {health_data['status']}, "
                           f"Requests: {stats_data['get_request_handlers()']['total_requests']}, "
                           f"Active WS: {stats_data['websocket_manager']['active_connections']}")
                
                # Alert on issues
                if health_data['status'] != 'healthy':
                    logging.error("System is not healthy!")
                
                # Wait for next interval
                time.sleep(interval)
                
            except requests.exceptions.RequestException as e:
                logging.error(f"Connection error: {e}")
                time.sleep(interval)
            except Exception as e:
                logging.error(f"Monitoring error: {e}")
                time.sleep(interval)

# Usage
monitor = HealthMonitor("http://localhost:8000")
monitor.monitor(interval=15)  # Check every 15 seconds
```

## Conclusion
The Health Monitoring API provides essential tools for ensuring the reliability and performance of the Praxis Agent system. The `/health` endpoint offers a simple way to verify service availability for container orchestration and load balancing, while the `/stats` endpoint delivers comprehensive metrics for detailed system analysis. By integrating these endpoints with monitoring tools like Prometheus and Grafana, teams can gain valuable insights into system performance, quickly identify issues, and maintain optimal operation. The provided code examples demonstrate practical ways to access and utilize the monitoring data for both development and production environments.

**Referenced Files in This Document**   
- [handlers.py](file://src/praxis_sdk/api/handlers.py#L27-L64)
- [server.py](file://src/praxis_sdk/api/server.py#L427-L460)
- [gateway.py](file://src/praxis_sdk/api/gateway.py#L529-L547)
- [websocket.py](file://src/praxis_sdk/api/websocket.py)
- [bus.py](file://src/praxis_sdk/bus.py)