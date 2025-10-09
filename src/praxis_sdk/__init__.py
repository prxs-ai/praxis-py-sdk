"""Praxis Python SDK - Distributed Agent Platform

A Python implementation of the Praxis agent system with P2P communication,
A2A protocol support, and comprehensive tooling integration.
"""

__version__ = "0.1.0"

from .agent import PraxisAgent, run_agent
from .bus import Event, EventBus, EventType, event_bus
from .config import PraxisConfig, load_config

__all__ = [
    "__version__",
    "PraxisAgent",
    "run_agent",
    "EventBus",
    "Event",
    "EventType",
    "event_bus",
    "PraxisConfig",
    "load_config",
]
