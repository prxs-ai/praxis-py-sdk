"""
Main entry point for Praxis Python SDK.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from loguru import logger

from .agent import PraxisAgent, run_agent
from .config import PraxisConfig, load_config


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.pass_context
def cli(ctx, debug: bool, config: Optional[str]):
    """Praxis Python SDK - Distributed Agent Platform"""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    ctx.obj['config'] = config


@cli.command()
@click.option('--name', '-n', default='orchestrator', help='Agent name')
@click.option('--port', '-p', type=int, help='API server port')
@click.option('--p2p-port', type=int, help='P2P service port')
@click.pass_context
def run(ctx, name: str, port: Optional[int], p2p_port: Optional[int]):
    """Run a Praxis agent"""
    config_file = ctx.obj.get('config')
    
    # Load configuration
    if config_file:
        config = PraxisConfig.load_from_yaml(config_file)
    else:
        config = PraxisConfig()
    
    # Override with command line options
    if port:
        config.api.port = port
    if p2p_port:
        config.p2p.port = p2p_port
    
    if ctx.obj.get('debug'):
        config.debug = True
        config.logging.level = "DEBUG"
    
    logger.info(f"Starting Praxis Agent '{name}'...")
    
    try:
        asyncio.run(run_agent_with_config(config, name))
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        sys.exit(1)


async def run_agent_with_config(config: PraxisConfig, agent_name: str):
    """Run agent with specific configuration."""
    agent = PraxisAgent(config, agent_name)
    await agent.start()


@cli.command()
@click.option('--output', '-o', default='./praxis.yaml', help='Output configuration file')
@click.option('--env', type=click.Choice(['development', 'production']), default='development', help='Environment')
def init_config(output: str, env: str):
    """Generate initial configuration file"""
    output_path = Path(output)
    
    if output_path.exists():
        if not click.confirm(f"File {output} already exists. Overwrite?"):
            return
    
    # Create default config and set environment
    config = PraxisConfig()
    config.environment = env
    
    config.save_to_yaml(output_path)
    logger.success(f"Configuration file created: {output}")


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
def validate_config(config: Optional[str]):
    """Validate configuration file"""
    try:
        if config:
            cfg = PraxisConfig.load_from_yaml(config)
        else:
            cfg = PraxisConfig()
        
        logger.success("Configuration is valid")
        
        # Print configuration summary
        click.echo("\nConfiguration Summary:")
        click.echo(f"Environment: {cfg.environment}")
        click.echo(f"Debug: {cfg.debug}")
        click.echo(f"API Port: {cfg.api.port}")
        click.echo(f"P2P Port: {cfg.p2p.port}")
        click.echo(f"P2P Enabled: {cfg.p2p.enabled}")
        click.echo(f"MCP Enabled: {cfg.mcp.enabled}")
        click.echo(f"Tools: {len(cfg.tools)}")
        click.echo(f"Agents: {len(cfg.agents)}")
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)


@cli.command()
def version():
    """Show version information"""
    from . import __version__
    click.echo(f"Praxis Python SDK v{__version__}")


def main():
    """Main CLI entry point."""
    cli()


if __name__ == '__main__':
    main()