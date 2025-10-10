"""Execution Engines Implementation

Python implementation of execution engines including DaggerExecutionEngine
which provides containerized execution using Docker SDK.
"""

import asyncio
import os
import shutil
import subprocess
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import docker
    from docker.errors import APIError, ContainerError, ImageNotFound

    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    ImageNotFound = Exception
    ContainerError = Exception
    APIError = Exception
    DOCKER_AVAILABLE = False

try:
    import dagger
    from dagger import dag

    DAGGER_AVAILABLE = True
except ImportError:
    dagger = None
    dag = None
    DAGGER_AVAILABLE = False

import httpx
from loguru import logger

from .contracts import (
    DaggerEngineSpec,
    ExecutionEngine,
    ExecutionError,
    LocalEngineSpec,
    RemoteMCPEngineSpec,
    ToolContract,
    ValidationError,
)


class DaggerExecutionEngine(ExecutionEngine):
    """Real Dagger Engine implementation using official Python Dagger SDK.
    Python equivalent of Go's DaggerEngine using actual Dagger Engine.
    """

    def __init__(self):
        if not DAGGER_AVAILABLE:
            raise RuntimeError(
                "Dagger SDK not available. Install with: pip install dagger-io"
            )

        # Dagger client is created per-connection in execute method
        self.connection_options = {}

    def configure_connection(self, **options):
        """Configure Dagger connection options.

        Args:
            **options: Connection options for dagger.Connection()

        """
        self.connection_options.update(options)

    async def execute(
        self,
        contract: ToolContract,
        args: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> str:
        """Execute a tool using the real Dagger Engine.

        Args:
            contract: Tool contract with Dagger engine spec
            args: Arguments to pass to the tool
            context: Optional execution context

        Returns:
            Tool execution output

        Raises:
            ExecutionError: If execution fails
            ValidationError: If contract is invalid

        """
        start_time = time.time()

        logger.info(f"⚡ REAL DAGGER ENGINE: Starting execution of '{contract.name}'")
        logger.info(f"   📊 Arguments: {args}")
        logger.info(f"   🔧 Context: {context}")

        try:
            # Validate and parse contract
            if not await self.validate_contract(contract):
                raise ValidationError(f"Invalid contract for tool '{contract.name}'")

            spec = contract.get_typed_spec()
            if not isinstance(spec, DaggerEngineSpec):
                raise ValidationError("Expected DaggerEngineSpec for dagger engine")

            logger.info(f"   📦 Container Image: {spec.image}")
            logger.info(f"   🔧 Command: {spec.command}")
            logger.info(f"   📂 Working Dir: {spec.working_dir or '/workspace'}")
            logger.info(f"   🔗 Mounts: {spec.mounts}")

            # Prepare environment variables like Go version
            env_vars = await self._prepare_environment_variables(
                spec, args, context or {}
            )

            logger.info(f"   🌍 Environment variables: {len(env_vars)}")
            for key in list(env_vars.keys())[:5]:  # Show first 5 env vars
                logger.info(
                    f"      🔑 {key}={env_vars[key][:50]}{'...' if len(env_vars[key]) > 50 else ''}"
                )

            logger.info("   ⚡ STEP 1: CONNECTING TO DAGGER ENGINE...")
            logger.info(f"      🔧 Connection config: {self.connection_options}")

            # Use Dagger connection exactly like Go version with log streaming
            logger.info("      🔧 Initializing Dagger connection with log streaming...")
            if not DAGGER_AVAILABLE or dagger is None:
                raise ExecutionError(
                    "Dagger is not available - this should have been caught in __init__"
                )

            # Add log output streaming like Go: dagger.WithLogOutput(os.Stdout)
            import sys

            # Create config with log output for streaming
            config = dagger.Config(log_output=sys.stdout)

            async with dagger.connection(config) as conn:
                logger.info("   ✅ STEP 1 SUCCESS: DAGGER ENGINE CONNECTED!")
                logger.info("      📡 Client established successfully")

                logger.info(
                    f"   📦 STEP 2: CREATING CONTAINER FROM IMAGE: {spec.image}"
                )
                logger.info(f"      🎯 Base image: {spec.image}")

                # Use dagger.dag which is the global client instance
                # This is the correct way to access Dagger methods in Python SDK
                client = dagger.dag
                logger.info(f"      🔧 Using dagger.dag as client: {type(client)}")

                # Create container from image (equivalent to Go: e.client.Container().From(image))
                container = client.container().from_(spec.image)
                logger.info("   ✅ STEP 2 SUCCESS: Container created from base image")

                # Mount directories (equivalent to Go: WithDirectory)
                logger.info(
                    f"   📁 STEP 3: MOUNTING DIRECTORIES ({len(spec.mounts)} mounts)"
                )
                mount_count = 0
                for host_path, container_path in spec.mounts.items():
                    mount_count += 1
                    abs_path = Path(host_path).resolve()

                    logger.info(
                        f"      📂 Mount {mount_count}/{len(spec.mounts)}: {abs_path} → {container_path}"
                    )

                    if not abs_path.exists():
                        logger.warning(
                            f"         ⚠️  Creating missing directory: {abs_path}"
                        )
                        abs_path.mkdir(parents=True, exist_ok=True)
                        logger.info("         ✅ Directory created successfully")
                    else:
                        logger.info("         ✅ Host directory exists")

                    # Mount host directory to container
                    logger.info("         🔄 Creating host directory reference...")
                    host_dir = client.host().directory(str(abs_path))
                    logger.info("         🔄 Mounting to container...")
                    container = container.with_directory(container_path, host_dir)
                    logger.info("         ✅ Mount completed successfully")

                if spec.mounts:
                    logger.info(
                        f"   ✅ STEP 3 SUCCESS: All {len(spec.mounts)} directories mounted"
                    )
                else:
                    logger.info("   ✅ STEP 3 SKIPPED: No directories to mount")

                # Set working directory if specified
                logger.info("   📂 STEP 4: SETTING WORKING DIRECTORY")
                if spec.working_dir:
                    logger.info(f"      📁 Setting workdir to: {spec.working_dir}")
                    container = container.with_workdir(spec.working_dir)
                    logger.info("   ✅ STEP 4 SUCCESS: Working directory set")
                else:
                    logger.info("   ✅ STEP 4 SKIPPED: Using default working directory")

                # Apply environment variables (equivalent to Go: WithEnvVariable)
                logger.info(
                    f"   🌍 STEP 5: APPLYING ENVIRONMENT VARIABLES ({len(env_vars)} vars)"
                )
                env_count = 0
                for key, value in env_vars.items():
                    if key and value is not None:
                        env_count += 1
                        logger.info(
                            f"      🔑 Env {env_count}: {key}={str(value)[:30]}{'...' if len(str(value)) > 30 else ''}"
                        )
                        container = container.with_env_variable(key, str(value))

                # Add cache-busting timestamp (like Go version)
                cache_bust = str(int(time.time() * 1000000000))
                logger.info(f"      🔄 Adding cache-busting: CACHE_BUST={cache_bust}")
                container = container.with_env_variable("CACHE_BUST", cache_bust)
                logger.info("   ✅ STEP 5 SUCCESS: All environment variables applied")

                # Add pip cache mounting for Python environments (optional optimization)
                logger.info("   💾 STEP 5.5: MOUNTING PIP CACHE (optional)")
                if "python" in spec.image.lower() or any(
                    "pip" in cmd for cmd in spec.command if isinstance(cmd, str)
                ):
                    try:
                        pip_cache_dir = Path.home() / ".cache" / "pip"
                        if pip_cache_dir.exists():
                            logger.info(
                                f"      📦 Mounting pip cache: {pip_cache_dir} → /root/.cache/pip"
                            )
                            host_pip_cache = client.host().directory(str(pip_cache_dir))
                            container = container.with_directory(
                                "/root/.cache/pip", host_pip_cache
                            )
                            logger.info("   ✅ STEP 5.5 SUCCESS: Pip cache mounted")
                        else:
                            logger.info(
                                "   ✅ STEP 5.5 SKIPPED: No pip cache directory found"
                            )
                    except Exception as cache_error:
                        logger.warning(
                            f"   ⚠️  STEP 5.5 WARNING: Could not mount pip cache: {cache_error}"
                        )
                else:
                    logger.info("   ✅ STEP 5.5 SKIPPED: Not a Python environment")

                logger.info("   🚀 STEP 6: EXECUTING COMMAND")
                logger.info(f"      💻 Command: {' '.join(spec.command)}")
                logger.info(f"      ⏱️  Timeout: {spec.timeout}s")
                logger.info("      🔄 Creating execution container...")

                # Check Dagger SDK version for debugging
                try:
                    if hasattr(dagger, "__version__"):
                        logger.info(
                            f"      📦 Dagger SDK version: {dagger.__version__}"
                        )
                    else:
                        logger.info("      📦 Dagger SDK version: Unknown")
                except:
                    logger.info("      📦 Could not determine Dagger SDK version")

                # Execute command (equivalent to Go: WithExec)
                exec_container = container.with_exec(spec.command)
                logger.info("   ✅ STEP 6 SUCCESS: Command execution started")

                logger.info(
                    "   📥 STEP 7: RETRIEVING EXECUTION RESULTS WITH LIVE STREAMING"
                )
                logger.info("      🔄 Starting container execution...")
                logger.info("      📡 === CONTAINER OUTPUT START ===")

                # Get stdout (equivalent to Go: Stdout(ctx)) - MUST be inside connection context
                logger.info("      🔄 Executing and streaming output...")

                try:
                    # Execute and get output with timeout
                    stdout_result = await asyncio.wait_for(
                        exec_container.stdout(), timeout=spec.timeout
                    )

                    # Stream the output line by line for visibility
                    if stdout_result:
                        for line in stdout_result.splitlines():
                            logger.info(f"      📤 [CONTAINER]: {line}")

                except Exception as e:
                    logger.error("      ❌ Container execution failed!")
                    stderr_text = ""
                    try:
                        stderr_text = await asyncio.wait_for(
                            exec_container.stderr(), timeout=5
                        )
                        if stderr_text:
                            logger.error(f"      📤 [STDERR]: {stderr_text}")
                    except Exception:
                        pass
                    raise ExecutionError(
                        f"Container command failed: {e}\n{stderr_text}"
                    )
                logger.info("      📡 === CONTAINER OUTPUT END ===")
                logger.info("   ✅ STEP 7 SUCCESS: Stdout retrieved successfully")

                execution_time = time.time() - start_time
                logger.info("   📋 DAGGER EXECUTION COMPLETED!")
                logger.info(f"      ⏱️  Total execution time: {execution_time:.2f}s")
                logger.info(f"      📊 Output size: {len(stdout_result)} characters")

                # Show container output in detail
                logger.info("   📄 STEP 8: PROCESSING CONTAINER OUTPUT")
                if stdout_result.strip():
                    lines = stdout_result.split("\n")
                    logger.info(
                        f"      📝 Container produced {len(lines)} lines of output"
                    )
                    logger.info("   📋 CONTAINER STDOUT (first 10 lines):")
                    for i, line in enumerate(lines[:10], 1):
                        if line.strip():
                            logger.info(f"      📝 [{i:2d}] {line}")
                    if len(lines) > 10:
                        logger.info(f"      📝 ... ({len(lines) - 10} more lines)")
                else:
                    logger.info("      📝 (no stdout output)")
                logger.info("   ✅ STEP 8 SUCCESS: Output processed")

                # Export modified directories back to host (like Go version)
                logger.info("   📤 STEP 9: EXPORTING MODIFIED DIRECTORIES")
                if spec.mounts:
                    logger.info(
                        f"      🔄 Exporting {len(spec.mounts)} mounted directories back to host..."
                    )
                    await self._export_modified_directories_dagger(
                        exec_container, spec, client
                    )
                    logger.info("   ✅ STEP 9 SUCCESS: Directory export completed")
                else:
                    logger.info("   ✅ STEP 9 SKIPPED: No directories to export")

                logger.info("   🎉 DAGGER ENGINE EXECUTION SUMMARY:")
                logger.info(f"      🎯 Tool: '{contract.name}'")
                logger.info(f"      ⏱️  Duration: {execution_time:.2f}s")
                logger.info(f"      📊 Output size: {len(stdout_result)} chars")
                logger.info(f"      🌍 Environment variables: {len(env_vars)}")
                logger.info(f"      📁 Directory mounts: {len(spec.mounts)}")
                logger.info(
                    "   ✅ REAL DAGGER SUCCESS: Execution completed successfully!"
                )

                return stdout_result

        except Exception as e:
            duration = time.time() - start_time
            logger.error("   ❌ DAGGER ENGINE CRITICAL ERROR!")
            logger.error(f"      🎯 Tool: '{contract.name}'")
            logger.error(f"      ⏱️  Duration: {duration:.2f}s")
            logger.error(f"      💥 Error: {str(e)}")
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Dagger execution failed: {str(e)}")

    async def validate_contract(self, contract: ToolContract) -> bool:
        """Validate if this engine can execute the given contract."""
        try:
            spec = contract.get_typed_spec()
            return isinstance(spec, DaggerEngineSpec)
        except Exception:
            return False

    async def get_capabilities(self) -> dict[str, Any]:
        """Get capabilities supported by this engine."""
        return {
            "engine_type": "dagger",
            "supports_containers": True,
            "supports_mounts": True,
            "supports_environment": True,
            "supports_resource_limits": False,  # Handled by Dagger Engine
            "dagger_available": DAGGER_AVAILABLE,
            "real_dagger_engine": True,
        }

    async def cleanup(self):
        """Cleanup Dagger Engine resources."""
        # Dagger Engine handles cleanup automatically
        # No manual cleanup needed like Docker SDK
        logger.debug("Dagger Engine cleanup completed")

    async def _prepare_environment_variables(
        self, spec: DaggerEngineSpec, args: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, str]:
        """Prepare environment variables for Dagger execution (like Go version)."""
        env_vars = {}

        # Add fixed environment variables from spec
        if spec.env:
            env_vars.update({k: str(v) for k, v in spec.env.items()})

        # Add passthrough environment variables from host (like Go version)
        for env_var in spec.env_passthrough or []:
            if env_var and env_var in os.environ:
                env_vars[env_var] = os.environ[env_var]

        # Add arguments as environment variables (like Go version)
        for key, value in args.items():
            if key:  # Skip empty keys
                env_vars[key] = str(value)

        # Add context variables
        for key, value in context.items():
            if key:
                context_key = f"CONTEXT_{key.upper()}"
                env_vars[context_key] = str(value)

        return env_vars

    async def _export_modified_directories_dagger(
        self, exec_container: Any, spec: DaggerEngineSpec, client: Any
    ):
        """Export modified directories from Dagger container back to host (like Go version)."""
        # Export modified directories back to host (equivalent to Go: Directory().Export())
        for host_path, container_path in spec.mounts.items():
            try:
                abs_path = Path(host_path).resolve()
                logger.info(f"   📤 EXPORTING: {container_path} → {abs_path}")

                # Export the directory from container back to host (like Go version)
                container_dir = exec_container.directory(container_path)
                await container_dir.export(str(abs_path))

                logger.debug(f"Successfully exported {container_path} to {abs_path}")
            except Exception as e:
                # Log warning but don't fail (like Go version behavior)
                logger.warning(f"Could not export {container_path} back to host: {e}")


class LocalExecutionEngine(ExecutionEngine):
    """Local execution engine using subprocess.
    Python equivalent of direct command execution.
    """

    async def execute(
        self,
        contract: ToolContract,
        args: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> str:
        """Execute a tool locally using subprocess."""
        start_time = time.time()

        logger.info(f"💻 LOCAL ENGINE: Starting execution of '{contract.name}'")
        logger.info(f"   📊 Arguments: {args}")
        logger.info(f"   🔧 Context: {context}")

        try:
            # Validate and parse contract
            if not await self.validate_contract(contract):
                raise ValidationError(f"Invalid contract for tool '{contract.name}'")

            spec = contract.get_typed_spec()
            if not isinstance(spec, LocalEngineSpec):
                raise ValidationError("Expected LocalEngineSpec for local engine")

            logger.info(f"   🔧 Command: {spec.command}")
            logger.info(f"   🐚 Shell: {spec.shell}")
            logger.info(f"   📁 Working Dir: {spec.cwd}")

            # Prepare environment
            env = os.environ.copy()
            env.update(spec.env)

            # Add arguments as environment variables
            for key, value in args.items():
                env[f"ARG_{key.upper()}"] = str(value)

            # Add context variables
            for key, value in (context or {}).items():
                env[f"CONTEXT_{key.upper()}"] = str(value)

            logger.info(f"   🌍 Environment: {len(env)} variables")

            # Execute command
            if spec.shell:
                command = " ".join(spec.command)
            else:
                command = spec.command

            logger.info("   🚀 STARTING LOCAL EXECUTION...")

            process = await asyncio.create_subprocess_exec(
                *(["/bin/sh", "-c", command] if spec.shell else command),
                stdout=asyncio.subprocess.PIPE if spec.capture_output else None,
                stderr=asyncio.subprocess.PIPE if spec.capture_output else None,
                cwd=spec.cwd,
                env=env,
            )

            logger.info(f"   ⏳ WAITING FOR COMPLETION (timeout: {spec.timeout}s)...")

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=spec.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                logger.error(f"   ❌ LOCAL EXECUTION TIMEOUT: after {spec.timeout}s")
                raise ExecutionError(
                    f"Tool '{contract.name}' timed out after {spec.timeout}s"
                )

            logger.info(f"   📋 PROCESS FINISHED: Exit code {process.returncode}")

            if process.returncode != 0:
                error_msg = (
                    stderr.decode("utf-8", errors="ignore")
                    if stderr
                    else f"Process exited with code {process.returncode}"
                )
                logger.error(f"   ❌ LOCAL EXECUTION FAILED: {error_msg[:200]}...")
                raise ExecutionError(
                    f"Tool '{contract.name}' failed: {error_msg}",
                    exit_code=process.returncode,
                    output=stdout.decode("utf-8", errors="ignore") if stdout else "",
                )

            duration = time.time() - start_time
            output = stdout.decode("utf-8", errors="ignore") if stdout else ""
            logger.info(
                f"   ✅ LOCAL SUCCESS: '{contract.name}' completed in {duration:.2f}s"
            )
            logger.info(f"   📤 Output: {output[:200]}...")

            return output

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Local tool '{contract.name}' failed after {duration:.2f}s: {e}"
            )
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Local execution failed: {str(e)}")

    async def validate_contract(self, contract: ToolContract) -> bool:
        """Validate if this engine can execute the given contract."""
        try:
            spec = contract.get_typed_spec()
            return isinstance(spec, LocalEngineSpec)
        except Exception:
            return False

    async def get_capabilities(self) -> dict[str, Any]:
        """Get capabilities supported by this engine."""
        return {
            "engine_type": "local",
            "supports_containers": False,
            "supports_mounts": False,
            "supports_environment": True,
            "supports_shell": True,
        }


class DockerSDKExecutionEngine(ExecutionEngine):
    """Docker SDK execution engine as fallback when Dagger is not available.
    Uses Docker Python SDK directly to execute tools in containers.
    """

    def __init__(self):
        if not DOCKER_AVAILABLE:
            raise RuntimeError(
                "Docker SDK not available. Install with: pip install docker"
            )

        # Docker client is created per-execution
        self._docker_client = None

    def _get_docker_client(self):
        """Get or create Docker client"""
        if self._docker_client is None:
            self._docker_client = docker.from_env()
        return self._docker_client

    async def execute(
        self,
        contract: ToolContract,
        args: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> str:
        """Execute a tool using Docker SDK."""
        start_time = time.time()

        logger.info(f"🐳 DOCKER SDK ENGINE: Starting execution of '{contract.name}'")
        logger.info(f"   📊 Arguments: {args}")
        logger.info(f"   🔧 Context: {context}")

        try:
            # Validate and parse contract
            if not await self.validate_contract(contract):
                raise ValidationError(f"Invalid contract for tool '{contract.name}'")

            spec = contract.get_typed_spec()
            if not isinstance(spec, DaggerEngineSpec):
                raise ValidationError("Expected DaggerEngineSpec for docker-sdk engine")

            logger.info(f"   📦 Container Image: {spec.image}")
            logger.info(f"   🔧 Command: {spec.command}")
            logger.info(f"   📂 Working Dir: {spec.working_dir or '/workspace'}")
            logger.info(f"   🔗 Mounts: {spec.mounts}")

            # Prepare environment variables
            env_vars = await self._prepare_environment_variables(
                spec, args, context or {}
            )

            logger.info(f"   🌍 Environment variables: {len(env_vars)}")

            logger.info("   🐳 STEP 1: CONNECTING TO DOCKER DAEMON...")
            client = self._get_docker_client()
            logger.info("   ✅ STEP 1 SUCCESS: Docker client connected")

            logger.info("   📦 STEP 2: CREATING CONTAINER")

            # Prepare volumes for mounts
            volumes = {}
            binds = []
            for host_path, container_path in spec.mounts.items():
                abs_path = Path(host_path).resolve()
                if not abs_path.exists():
                    abs_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"      📂 Created directory: {abs_path}")

                volumes[str(abs_path)] = {"bind": container_path, "mode": "rw"}
                binds.append(f"{abs_path}:{container_path}:rw")
                logger.info(f"      🔗 Mount: {abs_path} -> {container_path}")

            # Create and run container
            container = client.containers.run(
                image=spec.image,
                command=spec.command,
                environment=env_vars,
                volumes=volumes,
                working_dir=spec.working_dir or "/workspace",
                detach=True,
                remove=False,  # Keep container for debugging if needed
                stdout=True,
                stderr=True,
            )

            logger.info(
                f"   ✅ STEP 2 SUCCESS: Container created with ID: {container.id[:12]}"
            )
            logger.info(
                f"   ⏳ STEP 3: WAITING FOR COMPLETION (timeout: {spec.timeout}s)"
            )

            # Wait for container to complete
            try:
                result = container.wait(timeout=spec.timeout)
                exit_code = result["StatusCode"]

                logger.info(
                    f"   ✅ STEP 3 SUCCESS: Container completed with exit code: {exit_code}"
                )

                # Get output
                stdout = container.logs(stdout=True, stderr=False).decode(
                    "utf-8", errors="ignore"
                )
                stderr = container.logs(stdout=False, stderr=True).decode(
                    "utf-8", errors="ignore"
                )

                # Clean up container
                try:
                    container.remove()
                    logger.debug(f"Container {container.id[:12]} removed")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup container: {cleanup_error}")

                if exit_code != 0:
                    error_msg = stderr or f"Container exited with code {exit_code}"
                    logger.error(
                        f"   ❌ DOCKER SDK EXECUTION FAILED: {error_msg[:200]}..."
                    )
                    raise ExecutionError(
                        f"Tool '{contract.name}' failed: {error_msg}",
                        exit_code=exit_code,
                        output=stdout,
                    )

                logger.info("   🎉 DOCKER SDK ENGINE EXECUTION SUMMARY:")
                logger.info(f"      🎯 Tool: '{contract.name}'")
                logger.info(f"      ⏱️  Duration: {execution_time:.2f}s")
                logger.info(f"      📊 Output size: {len(stdout)} chars")
                logger.info(f"      🌍 Environment variables: {len(env_vars)}")
                logger.info(f"      📁 Directory mounts: {len(spec.mounts)}")
                logger.info(
                    "   ✅ DOCKER SDK SUCCESS: Execution completed successfully!"
                )

                return stdout

            except docker.errors.APIError as api_error:
                logger.error(f"   ❌ Docker API error: {api_error}")
                try:
                    container.remove()
                except:
                    pass
                raise ExecutionError(f"Docker API error: {str(api_error)}")

        except Exception as e:
            duration = time.time() - start_time
            logger.error("   ❌ DOCKER SDK ENGINE CRITICAL ERROR!")
            logger.error(f"      🎯 Tool: '{contract.name}'")
            logger.error(f"      ⏱️  Duration: {duration:.2f}s")
            logger.error(f"      💥 Error: {str(e)}")
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Docker SDK execution failed: {str(e)}")

    async def validate_contract(self, contract: ToolContract) -> bool:
        """Validate if this engine can execute the given contract."""
        try:
            spec = contract.get_typed_spec()
            return isinstance(spec, DaggerEngineSpec)  # Same spec format as Dagger
        except Exception:
            return False

    async def get_capabilities(self) -> dict[str, Any]:
        """Get capabilities supported by this engine."""
        return {
            "engine_type": "docker-sdk",
            "supports_containers": True,
            "supports_mounts": True,
            "supports_environment": True,
            "supports_resource_limits": False,
            "docker_available": DOCKER_AVAILABLE,
            "fallback_for_dagger": True,
        }

    async def cleanup(self):
        """Cleanup Docker SDK resources."""
        if self._docker_client:
            self._docker_client.close()
            self._docker_client = None
        logger.debug("Docker SDK client cleanup completed")

    async def _prepare_environment_variables(
        self, spec: DaggerEngineSpec, args: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, str]:
        """Prepare environment variables for Docker SDK execution (same as Dagger version)."""
        env_vars = {}

        # Add fixed environment variables from spec
        if spec.env:
            env_vars.update({k: str(v) for k, v in spec.env.items()})

        # Add passthrough environment variables from host
        for env_var in spec.env_passthrough or []:
            if env_var and env_var in os.environ:
                env_vars[env_var] = os.environ[env_var]

        # Add arguments as environment variables
        for key, value in args.items():
            if key:  # Skip empty keys
                env_vars[key] = str(value)

        # Add context variables
        for key, value in context.items():
            if key:
                context_key = f"CONTEXT_{key.upper()}"
                env_vars[context_key] = str(value)

        return env_vars


class RemoteMCPEngine(ExecutionEngine):
    """Remote MCP execution engine using HTTP requests.
    Python equivalent of Go's RemoteMCPEngine.
    """

    def __init__(self, timeout: int = 300):
        self.default_timeout = timeout
        self._http_client = None

    @asynccontextmanager
    async def _get_http_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()

        try:
            yield self._http_client
        finally:
            pass  # Keep client alive for reuse

    async def execute(
        self,
        contract: ToolContract,
        args: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> str:
        """Execute a tool on remote MCP server."""
        start_time = time.time()

        try:
            # Validate and parse contract
            if not await self.validate_contract(contract):
                raise ValidationError(f"Invalid contract for tool '{contract.name}'")

            spec = contract.get_typed_spec()
            if not isinstance(spec, RemoteMCPEngineSpec):
                raise ValidationError(
                    "Expected RemoteMCPEngineSpec for remote-mcp engine"
                )

            # Prepare request
            url = f"{spec.address.rstrip('/')}/tool/{contract.name}"
            headers = {"Content-Type": "application/json"}
            headers.update(spec.headers)

            if spec.auth_token:
                headers["Authorization"] = f"Bearer {spec.auth_token}"

            # Merge args and context
            payload = {**args}
            if context:
                payload.update(context)

            # Make request
            async with self._get_http_client() as client:
                response = await client.post(
                    url, json=payload, headers=headers, timeout=spec.timeout
                )

                if response.status_code != 200:
                    raise ExecutionError(
                        f"Remote tool '{contract.name}' failed with status {response.status_code}: {response.text}"
                    )

                duration = time.time() - start_time
                logger.info(
                    f"Remote tool '{contract.name}' completed in {duration:.2f}s"
                )

                # Return response text or JSON if possible
                try:
                    result = response.json()
                    if isinstance(result, dict) and "result" in result:
                        return str(result["result"])
                    return str(result)
                except:
                    return response.text

        except httpx.RequestError as e:
            raise ExecutionError(
                f"Network error executing remote tool '{contract.name}': {str(e)}"
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Remote tool '{contract.name}' failed after {duration:.2f}s: {e}"
            )
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Remote execution failed: {str(e)}")

    async def validate_contract(self, contract: ToolContract) -> bool:
        """Validate if this engine can execute the given contract."""
        try:
            spec = contract.get_typed_spec()
            return isinstance(spec, RemoteMCPEngineSpec)
        except Exception:
            return False

    async def get_capabilities(self) -> dict[str, Any]:
        """Get capabilities supported by this engine."""
        return {
            "engine_type": "remote-mcp",
            "supports_containers": False,
            "supports_mounts": False,
            "supports_environment": False,
            "supports_http": True,
            "supports_authentication": True,
        }

    async def cleanup(self):
        """Cleanup HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Utility functions for engine management


def create_dagger_engine() -> DaggerExecutionEngine:
    """Create a new Dagger execution engine using real Dagger SDK.

    Returns:
        DaggerExecutionEngine instance

    Raises:
        RuntimeError: If Dagger SDK is not available

    """
    return DaggerExecutionEngine()


def create_local_engine() -> LocalExecutionEngine:
    """Create a new local execution engine.

    Returns:
        LocalExecutionEngine instance

    """
    return LocalExecutionEngine()


def create_docker_sdk_engine() -> DockerSDKExecutionEngine:
    """Create a new Docker SDK execution engine.

    Returns:
        DockerSDKExecutionEngine instance

    Raises:
        RuntimeError: If Docker SDK is not available

    """
    return DockerSDKExecutionEngine()


def create_remote_engine(timeout: int = 300) -> RemoteMCPEngine:
    """Create a new remote MCP execution engine.

    Args:
        timeout: Default timeout for requests

    Returns:
        RemoteMCPEngine instance

    """
    return RemoteMCPEngine(timeout=timeout)


async def is_docker_available() -> bool:
    """Test if Docker is available and working.

    Returns:
        True if Docker is available

    """
    if not DOCKER_AVAILABLE:
        return False

    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


async def test_dagger_availability() -> bool:
    """Test if Dagger Engine is available and working.

    Returns:
        True if Dagger is available

    """
    if not DAGGER_AVAILABLE:
        logger.debug("Dagger SDK not imported")
        return False

    logger.info("🔍 TESTING DAGGER ENGINE AVAILABILITY...")

    try:
        logger.info("   STEP 1: Checking Dagger CLI availability...")
        import subprocess

        result = subprocess.run(
            ["dagger", "version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                f"   ❌ Dagger CLI not available or not working: {result.stderr}"
            )
            return False
        logger.info(f"   ✅ Dagger CLI available: {result.stdout.strip()}")

        logger.info("   STEP 2: Checking Docker CLI availability...")
        docker_result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if docker_result.returncode != 0:
            logger.warning("   ❌ Docker CLI not available - required by Dagger Engine")
            return False
        logger.info(f"   ✅ Docker CLI available: {docker_result.stdout.strip()}")

        logger.info("   STEP 3: Testing Dagger Engine connection with retry logic...")

        # Retry logic with exponential backoff
        max_retries = 3
        base_delay = 2.0
        timeout_seconds = 60  # Increased from 30 to 60 seconds

        for attempt in range(max_retries):
            logger.info(f"      Attempt {attempt + 1}/{max_retries}...")

            try:
                # Simplified connection test with extended timeout
                async with asyncio.timeout(timeout_seconds):
                    logger.info(
                        f"      🔄 Creating Dagger connection (timeout: {timeout_seconds}s)..."
                    )

                    async with dagger.Connection() as client:
                        logger.info("      ✅ Dagger connection established!")

                        # Simplified test - just check if we can create a basic container reference
                        logger.info("      🔄 Testing basic container operation...")
                        container = client.container().from_("alpine:latest")
                        logger.info("      ✅ Basic container operation successful!")

                        logger.info("   ✅ DAGGER ENGINE AVAILABLE AND WORKING!")
                        return True

            except asyncio.TimeoutError:
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"      ⏰ Connection attempt {attempt + 1} timed out after {timeout_seconds}s"
                )

                if attempt < max_retries - 1:
                    logger.info(f"      ⏳ Waiting {delay}s before retry...")
                    await asyncio.sleep(delay)
                else:
                    logger.warning(
                        f"   ❌ All {max_retries} connection attempts timed out"
                    )
                    return False

            except Exception as conn_error:
                error_str = str(conn_error)
                logger.warning(
                    f"      ❌ Connection attempt {attempt + 1} failed: {error_str}"
                )

                # Check for known GraphQL schema issues
                if "includeDeprecated" in error_str and "Unknown argument" in error_str:
                    logger.warning(
                        "      🔧 Known GraphQL schema compatibility issue detected"
                    )
                    logger.warning(
                        "      🔧 This is a compatibility issue between Dagger versions"
                    )

                    try:
                        logger.info("      🔄 Attempting simplified connection...")
                        async with asyncio.timeout(
                            30
                        ):  # Shorter timeout for workaround
                            async with dagger.Connection() as client:
                                container = client.container().from_("alpine:latest")
                                logger.info(
                                    "      ✅ Workaround successful - basic operations work"
                                )
                                return True
                    except Exception as workaround_error:
                        logger.warning(
                            f"      ❌ Workaround failed: {workaround_error}"
                        )

                        # Only log detailed error on final attempt
                        if attempt == max_retries - 1:
                            logger.error("   ❌ DAGGER ENGINE COMPATIBILITY ISSUE:")
                            logger.error(
                                f"      - Dagger CLI version: {result.stdout.strip()}"
                            )
                            logger.error(f"      - GraphQL schema error: {error_str}")
                            logger.error(
                                "      - This is a known issue with gql library version 4.0.0+"
                            )
                            logger.error(
                                "      - Recommended fix: downgrade gql or upgrade Dagger"
                            )
                            logger.error(
                                "      - Will fallback to Docker SDK execution engine"
                            )

                        return False
                else:
                    # For other errors, retry with exponential backoff
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        logger.info(f"      ⏳ Waiting {delay}s before retry...")
                        await asyncio.sleep(delay)
                    else:
                        logger.warning(
                            f"   ❌ All {max_retries} attempts failed. Last error: {error_str}"
                        )
                        return False

    except subprocess.TimeoutExpired:
        logger.warning("   ❌ Dagger CLI or Docker CLI check timed out")
        return False
    except Exception as e:
        logger.warning(f"   ❌ Dagger availability test failed: {e}")
        return False
