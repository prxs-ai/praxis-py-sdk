from typing import Any

import httpx

from base_agent.domain_knowledge.config import LightRagConfig


class LightRagClient:
    def __init__(self, config: LightRagConfig):
        self.url = config.url
        self.timeout = config.timeout
        self.endpoints = config.endpoints

    def post(self, endpoint: str, json: dict[str, Any]) -> dict:
        url = f"{self.url}{endpoint}"

        try:
            response = httpx.post(url, json=json, timeout=self.timeout)
            response.raise_for_status()

            if endpoint == self.endpoints.query:
                # If a string is returned (e.g., cache hit), it's directly returned.
                # Otherwise, an async generator may be used to build the response.
                # https://github.com/HKUDS/LightRAG/blob/cac0f3ddc6bffa1f28de5fcdfbfde728c51364f8/lightrag/api/routers/query_routes.py#L154
                # 6.03.2025
                return [{"domain_knowledge": response.text}]

            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            print(f"Request error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

        return {}


def light_rag_client(config: LightRagConfig) -> LightRagClient:
    return LightRagClient(config=config)
