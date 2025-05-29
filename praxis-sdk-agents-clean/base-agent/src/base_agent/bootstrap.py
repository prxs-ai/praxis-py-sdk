import json
from typing import Any


def bootstrap_main(agent_cls):
    """Bootstrap a main agent with the necessary components to be able to run as a Ray Serve deployment."""
    from ray import serve

    @serve.deployment(name="base-agent-deployment", num_replicas=1)
    class AgentDeployment:
        def __init__(self, *args, **kwargs):
            # Композиция вместо наследования
            self._agent_cls = agent_cls
            self._agent_instance = None
            self._initialization_complete = False

            print("[INFO] AgentDeployment initialized")

        async def _ensure_initialized(self):
            """Асинхронная инициализация компонентов."""
            if self._initialization_complete:
                return

            try:
                print("[INFO] Starting async initialization...")

                # Создаем инстанс агента
                if self._agent_instance is None:
                    try:
                        from base_agent.config import get_agent_config

                        config = get_agent_config()
                        self._agent_instance = self._agent_cls(config)
                        print("[INFO] Agent instance created")
                    except Exception as e:
                        print(f"[WARNING] Failed to create agent instance: {e}")

                # Создаем основные компоненты
                try:
                    from base_agent.orchestration import workflow_builder
                    from base_agent.card import card_builder

                    self._runner = workflow_builder()
                    self._card = card_builder()

                    print("[INFO] Core components created")
                except Exception as e:
                    print(f"[WARNING] Failed to create components: {e}")

                # Инициализация libp2p (опционально)
                libp2p_initialized = False
                try:
                    print("[INFO] Starting libp2p initialization...")
                    from base_agent.p2p import setup_libp2p
                    await setup_libp2p()
                    libp2p_initialized = True
                    print("[INFO] Libp2p setup completed successfully.")
                    
                    # ДОБАВЛЯЕМ ПЕЧАТЬ PEER INFO
                    try:
                        from base_agent.p2p import print_peer_info
                        print_peer_info()
                    except Exception as e:
                        print(f"[WARNING] Failed to print peer info: {e}")
                except RuntimeError as e:
                    print(f"[WARNING] Libp2p setup failed - async context error: {e}")
                except ImportError as e:
                    print(f"[WARNING] Libp2p setup failed - import error: {e}")
                except Exception as e:
                    print(f"[WARNING] Libp2p setup failed: {e}")
                    import traceback
                    traceback.print_exc()
                
                if not libp2p_initialized:
                    print("[WARNING] LibP2P not initialized - peer info not available")
                
                # Сохраняем статус libp2p для health checks
                self._libp2p_initialized = libp2p_initialized

                # Инициализация workflow runner
                try:
                    print("[INFO] Starting background workflows...")
                    self._runner.start_daemon()
                    self._runner.run_background_workflows()
                    print("[INFO] Background workflows started.")
                except Exception as e:
                    print(f"[WARNING] Failed to start background workflows: {e}")

                self._initialization_complete = True
                print("[INFO] Async initialization completed")

            except Exception as e:
                print(f"[ERROR] Async initialization failed: {e}")
                import traceback

                traceback.print_exc()
                raise

        async def __call__(self, request):
            """Основной обработчик HTTP запросов."""
            try:
                await self._ensure_initialized()

                path = request.url.path.strip("/")
                method = request.method

                # Импортируем Response локально
                from starlette.responses import JSONResponse

                print(f"[INFO] Handling request: {method} /{path}")

                # Маршрутизация
                if path == "card" and method == "GET":
                    if hasattr(self, "_card") and self._card:
                        return JSONResponse(self._card.model_dump())
                    else:
                        return JSONResponse({"error": "Card not available"})

                elif path == "peer" and method == "GET":
                    """Endpoint для получения информации о peer"""
                    try:
                        from base_agent.p2p import get_peer_info_formatted
                        
                        peer_info = get_peer_info_formatted()
                        if peer_info:
                            return JSONResponse(peer_info)
                        else:
                            return JSONResponse({"error": "Peer info not available", "libp2p_initialized": False})
                    except Exception as e:
                        return JSONResponse({"error": f"Failed to get peer info: {e}"})

                elif path == "health" and method == "GET":
                    try:
                        from base_agent.p2p import get_libp2p_status, get_peer_info_formatted

                        libp2p_status = get_libp2p_status()
                        peer_info = get_peer_info_formatted()
                    except Exception as e:
                        libp2p_status = {"initialized": False, "error": str(e)}
                        peer_info = None

                    health_data = {
                        "status": "healthy",
                        "initialized": self._initialization_complete,
                        "agent_class": str(self._agent_cls.__name__),
                        "agent_available": self._agent_instance is not None,
                        "libp2p": libp2p_status,
                        "libp2p_initialized": getattr(self, "_libp2p_initialized", False),
                        "peer_info": peer_info,
                        "components": {
                            "runner": hasattr(self, "_runner") and self._runner is not None,
                            "card": hasattr(self, "_card") and self._card is not None,
                            "agent": self._agent_instance is not None,
                        }
                    }
                    return JSONResponse(health_data)

                elif path == "debug" and method == "GET":
                    """Endpoint для расширенной диагностики libp2p"""
                    try:
                        from base_agent.p2p import diagnose_libp2p_environment, get_libp2p_status, get_peer_info_formatted
                        
                        debug_data = {
                            "libp2p_status": get_libp2p_status(),
                            "peer_info": get_peer_info_formatted(),
                            "environment": diagnose_libp2p_environment(),
                            "initialization_status": {
                                "completed": self._initialization_complete,
                                "libp2p_initialized": getattr(self, "_libp2p_initialized", False),
                                "components": {
                                    "runner": hasattr(self, "_runner") and self._runner is not None,
                                    "card": hasattr(self, "_card") and self._card is not None,
                                    "agent": self._agent_instance is not None,
                                }
                            }
                        }
                        return JSONResponse(debug_data)
                    except Exception as e:
                        return JSONResponse({"error": f"Debug endpoint error: {e}"})

                elif path == "workflows" and method == "GET":
                    if hasattr(self, "_runner") and self._runner:
                        try:
                            status = request.query_params.get("status")
                            workflows = await self._runner.list_workflows(status)
                            return JSONResponse(workflows)
                        except Exception as e:
                            return JSONResponse({"error": f"Failed to list workflows: {e}"})
                    else:
                        return JSONResponse({"error": "Workflow runner not available"})

                elif method == "POST":
                    # Обработка POST запросов
                    goal = path if path else "default_goal"

                    # Парсим body
                    body_data = {}
                    try:
                        body = await request.body()
                        if body:
                            body_data = json.loads(body)
                    except Exception as e:
                        print(f"[WARNING] Could not parse body: {e}")

                    plan = body_data.get("plan")
                    context = body_data.get("context")

                    if self._agent_instance and hasattr(self._agent_instance, "handle"):
                        try:
                            result = await self._agent_instance.handle(goal, plan, context)
                            response_data = result.model_dump() if hasattr(result, "model_dump") else result
                            return JSONResponse(response_data)
                        except Exception as e:
                            print(f"[ERROR] Agent handle error: {e}")
                            return JSONResponse({"error": f"Agent handle error: {e}", "goal": goal}, status_code=500)
                    else:
                        return JSONResponse(
                            {
                                "message": "Goal received but agent not available",
                                "goal": goal,
                                "body_data": body_data,
                                "status": "processed",
                            }
                        )

                else:
                    # 404
                    return JSONResponse(
                        {
                            "error": "Not found",
                            "path": path,
                            "method": method,
                            "available_endpoints": [
                                "GET /card", 
                                "GET /peer",
                                "GET /health", 
                                "GET /debug", 
                                "GET /workflows", 
                                "POST /{goal}"
                            ],
                        },
                        status_code=404,
                    )

            except Exception as e:
                from starlette.responses import JSONResponse

                print(f"[ERROR] Handler error: {e}")
                import traceback

                traceback.print_exc()
                return JSONResponse({"error": "Internal server error", "message": str(e)}, status_code=500)

        # НЕОБХОДИМЫЕ МЕТОДЫ ДЛЯ СОВМЕСТИМОСТИ

        async def get_card(self):
            """Метод get_card для совместимости с entrypoint.py"""
            try:
                await self._ensure_initialized()
                print("[INFO] Get_card method called")
                
                if hasattr(self, "_card") and self._card:
                    return self._card.model_dump()
                else:
                    return {"error": "Card not available"}
            except Exception as e:
                print(f"[ERROR] Get_card method error: {e}")
                import traceback
                traceback.print_exc()
                return {"error": str(e)}

        async def chat(self, message: str, action: str = None, session_uuid: str = None):
            """Метод chat для совместимости с entrypoint.py"""
            try:
                await self._ensure_initialized()
                print(
                    f"[INFO] Chat method called: message='{message}', action='{action}', session_uuid='{session_uuid}'"
                )

                if self._agent_instance and hasattr(self._agent_instance, "chat"):
                    # Вызываем метод chat агента
                    result = self._agent_instance.chat(message, action, session_uuid)
                    return result
                else:
                    # Возвращаем простой ответ
                    return {
                        "response_text": f"Received message: {message}",
                        "action": action,
                        "session_uuid": session_uuid,
                        "agent_available": self._agent_instance is not None,
                    }

            except Exception as e:
                print(f"[ERROR] Chat method error: {e}")
                import traceback

                traceback.print_exc()
                return {"response_text": "Error processing chat message", "error": str(e)}

        async def handle(self, goal: str, plan: dict = None, context: Any = None):
            """Метод handle для совместимости"""
            try:
                await self._ensure_initialized()
                print(f"[INFO] Handle method called: goal='{goal}'")

                if self._agent_instance and hasattr(self._agent_instance, "handle"):
                    result = await self._agent_instance.handle(goal, plan, context)
                    return result
                else:
                    return {"goal": goal, "plan": plan, "context": context, "status": "handled but agent not available"}

            except Exception as e:
                print(f"[ERROR] Handle method error: {e}")
                import traceback

                traceback.print_exc()
                return {"goal": goal}

        async def list_workflows(self, status: str = None):
            """Метод list_workflows для совместимости с entrypoint.py"""
            try:
                await self._ensure_initialized()
                print(f"[INFO] List_workflows method called: status='{status}'")
                
                if hasattr(self, "_runner") and self._runner:
                    workflows = await self._runner.list_workflows(status)
                    return workflows
                else:
                    return {"error": "Workflow runner not available"}
            except Exception as e:
                print(f"[ERROR] List_workflows method error: {e}")
                import traceback
                traceback.print_exc()
                return {"error": str(e)}

        # ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ДЛЯ ПОЛНОЙ СОВМЕСТИМОСТИ

        @property
        def workflow_runner(self):
            """Свойство для доступа к workflow runner"""
            return getattr(self, "_runner", None)

        @property
        def agent_card(self):
            """Свойство для доступа к agent card"""
            return getattr(self, "_card", None)

    return AgentDeployment
