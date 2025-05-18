from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from base_agent.domain_knowledge.config import LightRagConfig, retries

# ------  Retries --------- #
stop = stop_after_attempt(retries.stop_attempts)
wait = wait_exponential(
    multiplier=retries.wait_multiplier,
    min=retries.wait_min,
    max=retries.wait_max,
)


class LightRagClient:
    def __init__(self, config: LightRagConfig):
        self.url = config.url
        self.timeout = config.timeout
        self.endpoints = config.endpoints

    @retry(
        stop=stop,
        wait=wait,
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

    @retry(
        stop=stop,
        wait=wait,
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get(self, endpoint: str, params: dict[str, Any]) -> dict:
        url = f"{self.url}{endpoint}"

        try:
            response = httpx.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
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
