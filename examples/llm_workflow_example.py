#!/usr/bin/env python3
"""
Example usage of LLM Workflow Planning.

This example demonstrates:
- Natural language to DSL conversion
- Workflow plan generation and optimization
- Integration with existing DSL execution engine
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from praxis_sdk.llm import (
    WorkflowPlanner,
    OptimizationGoal,
    PlanningRequest,
    get_workflow_generation_prompt
)
from praxis_sdk.p2p.service import P2PService
from praxis_sdk.mcp.registry import MCPRegistry
from praxis_sdk.config import PraxisConfig


async def main():
    """Example usage of LLM Workflow Planning."""
    
    print("🚀 LLM Workflow Planning Example")
    print("=" * 50)
    
    # Mock configuration (in real usage, this would come from config file)
    config = PraxisConfig()
    
    # Mock P2P service and MCP registry (simplified for example)
    class MockP2PService:
        async def get_all_agent_cards(self):
            return {
                "agent1": {
                    "id": "filesystem-agent",
                    "capabilities": {
                        "file_read": {"description": "Read files", "parameters": {}},
                        "file_write": {"description": "Write files", "parameters": {}},
                        "file_list": {"description": "List directory contents", "parameters": {}}
                    },
                    "load": {"current": 0.2, "max": 1.0},
                    "location": "local",
                    "metadata": {}
                },
                "agent2": {
                    "id": "web-agent", 
                    "capabilities": {
                        "http_request": {"description": "Make HTTP requests", "parameters": {}},
                        "web_scrape": {"description": "Scrape web pages", "parameters": {}}
                    },
                    "load": {"current": 0.1, "max": 1.0},
                    "location": "remote",
                    "metadata": {}
                }
            }
    
    class MockMCPRegistry:
        async def discover_all_tools(self):
            return {
                "filesystem": [
                    {"name": "file_read", "description": "Read file contents", "inputSchema": {"properties": {}}},
                    {"name": "file_write", "description": "Write file contents", "inputSchema": {"properties": {}}},
                    {"name": "file_list", "description": "List directory", "inputSchema": {"properties": {}}}
                ],
                "web": [
                    {"name": "http_request", "description": "HTTP request", "inputSchema": {"properties": {}}},
                    {"name": "web_scrape", "description": "Web scraping", "inputSchema": {"properties": {}}}
                ]
            }
    
    # Initialize services
    p2p_service = MockP2PService()
    mcp_registry = MockMCPRegistry()
    
    # Initialize workflow planner
    print("🔧 Initializing Workflow Planner...")
    planner = WorkflowPlanner(
        p2p_service=p2p_service,
        mcp_registry=mcp_registry,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    await planner.initialize()
    print("✅ Workflow Planner initialized")
    
    # Example 1: Simple file operation
    print("\n📝 Example 1: File Operations")
    print("-" * 30)
    
    user_request1 = "Create a backup of my important files and list them"
    result1 = await planner.generate_from_natural_language(user_request1)
    
    if result1.success:
        print(f"✅ Generated workflow plan: {result1.workflow_plan.id}")
        print(f"📋 Description: {result1.workflow_plan.description}")
        print(f"⚙️  DSL Commands:")
        for line in result1.workflow_plan.dsl.split('\n'):
            if line.strip():
                print(f"   {line}")
        print(f"⏱️  Estimated time: {result1.workflow_plan.estimated_time} minutes")
        print(f"🔧 Processing time: {result1.processing_time:.2f}s")
        
        # Show execution plan
        if result1.execution_plan:
            print(f"📊 Execution Plan: {len(result1.execution_plan.steps)} steps")
            for step in result1.execution_plan.steps[:3]:  # Show first 3 steps
                agent = result1.execution_plan.agent_assignments.get(step["id"], "unknown")
                print(f"   Step {step['id']}: {step['tool']} -> {agent}")
    else:
        print(f"❌ Failed: {result1.error_message}")
    
    # Example 2: Web scraping workflow
    print("\n🌐 Example 2: Web Analysis")
    print("-" * 30)
    
    user_request2 = "Check the status of my website and save a report"
    result2 = await planner.generate_from_natural_language(
        user_request2,
        optimization_goals=[OptimizationGoal.PERFORMANCE]
    )
    
    if result2.success:
        print(f"✅ Generated workflow plan: {result2.workflow_plan.id}")
        print(f"📋 Description: {result2.workflow_plan.description}")
        print(f"⚙️  DSL Commands:")
        for line in result2.workflow_plan.dsl.split('\n'):
            if line.strip():
                print(f"   {line}")
        
        if result2.optimization_applied:
            print(f"🚀 Optimization applied with improvements")
            optimizations = result2.workflow_plan.metadata.get("optimization", {})
            if "improvements" in optimizations:
                for improvement in optimizations["improvements"][:2]:  # Show first 2
                    print(f"   • {improvement}")
    else:
        print(f"❌ Failed: {result2.error_message}")
    
    # Example 3: Network status and suggestions
    print("\n📊 Network Status")
    print("-" * 30)
    
    network_status = await planner.get_network_status()
    print(f"🤖 Active agents: {network_status.get('agents', 0)}")
    print(f"🛠️  Available tools: {network_status.get('tools', 0)}")
    print(f"📈 Network load: {network_status.get('network_load', 'unknown')}")
    print(f"🧠 LLM available: {'Yes' if network_status.get('llm_available', False) else 'No'}")
    
    # Show planner statistics
    stats = planner.get_statistics()
    print(f"\n📈 Planner Statistics:")
    print(f"   Total requests: {stats['total_requests']}")
    print(f"   Success rate: {stats['success_rate']:.1%}")
    print(f"   LLM usage: {stats['llm_usage_rate']:.1%}")
    print(f"   Fallback usage: {stats['fallback_rate']:.1%}")
    print(f"   Avg processing time: {stats['average_processing_time']:.2f}s")
    
    # Example 4: Planning suggestions
    print("\n💡 Planning Suggestions")
    print("-" * 30)
    
    partial_request = "I need to analyze some data"
    suggestions = await planner.get_planning_suggestions(partial_request)
    print(f"For '{partial_request}':")
    for suggestion in suggestions:
        print(f"   • {suggestion}")
    
    print("\n🎉 Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())