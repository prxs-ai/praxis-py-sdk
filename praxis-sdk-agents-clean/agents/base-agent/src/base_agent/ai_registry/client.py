from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from base_agent.ai_registry.config import AiRegistryConfig


class AiRegistryClient:
    def __init__(self, config: AiRegistryConfig):
        self.url = config.url
        self.timeout = config.timeout
        self.endpoints = config.endpoints

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def post(self, endpoint: str, json: dict[str, Any]) -> dict:
        url = f"{self.url}{endpoint}"

        try:
            response = httpx.post(url, json=json, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            print(f"Request error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

        return {}
