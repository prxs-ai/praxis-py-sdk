import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import trio
from cryptography.fernet import Fernet, InvalidToken
from loguru import logger

from ..keyring_manager import get_keyring_manager


class EncryptedKVStore:
    """
    Encrypted key-value store.

    Data is encrypted at rest using Fernet symmetric encryption.
    Each agent can have multiple namespaces for organizing data.
    """

    MASTER_KEY_NAME = "PRAXIS_STORAGE_MASTER_KEY"

    def __init__(
        self,
        agent_name: str,
        namespace: str = "default",
        storage_dir: Optional[Path] = None,
    ):
        """
        Initialize encrypted KV store.

        Args:
            agent_name: Name of the agent (used for directory isolation)
            namespace: Namespace for this store instance
            storage_dir: Base directory for storage (default: ./data/encrypted_store)
        """
        self.agent_name = agent_name
        self.namespace = namespace

        if storage_dir is None:
            storage_dir = Path("data") / "encrypted_store"
        self.storage_dir = storage_dir
        self.agent_dir = self.storage_dir / agent_name
        self.namespace_file = self.agent_dir / f"{namespace}.enc"

        self.keyring_manager = get_keyring_manager()
        self._fernet: Optional[Fernet] = None
        self._lock = asyncio.Lock()
        self._cache: Dict[str, Any] = {}
        self._loaded = False

        logger.info(
            f"Encrypted KV store initialized: agent={agent_name}, "
            f"namespace={namespace}, path={self.namespace_file}"
        )

    async def _ensure_initialized(self) -> None:
        """Ensure encryption key and storage directories are ready."""
        if self._fernet is not None:
            return

        master_key = self._get_or_create_master_key()
        self._fernet = Fernet(master_key)

        self.agent_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"KV store initialized: {self.namespace_file}")

    def _get_or_create_master_key(self) -> bytes:
        """
        Get or create master encryption key.

        Priority:
        1. KeyringManager (system keyring)
        2. Environment variable PRAXIS_MASTER_KEY
        3. Generate new key and store in keyring
        """
        key_str = self.keyring_manager.get_credential(
            self.MASTER_KEY_NAME,
            fallback_env="PRAXIS_MASTER_KEY"
        )

        if key_str:
            logger.debug("Master key retrieved from keyring/environment")
            return key_str.encode()

        logger.warning("No master key found, generating new key")
        new_key = Fernet.generate_key()
        key_str = new_key.decode()

        if self.keyring_manager.set_credential(self.MASTER_KEY_NAME, key_str):
            logger.info("Master key generated and stored in keyring")
        else:
            logger.warning(
                "Could not store master key in keyring. "
                f"Set {self.MASTER_KEY_NAME} environment variable to persist."
            )

        return new_key

    async def _load_data(self) -> Dict[str, Any]:
        """
        Load and decrypt data from disk.
        """
        await self._ensure_initialized()

        if not self.namespace_file.exists():
            logger.debug(f"Namespace file does not exist: {self.namespace_file}")
            return {}

        try:
            async with await trio.open_file(self.namespace_file, "rb") as f:
                encrypted_data = await f.read()

            if not encrypted_data:
                return {}

            assert self._fernet is not None
            decrypted_data = self._fernet.decrypt(encrypted_data)
            data = json.loads(decrypted_data.decode())

            logger.debug(f"Loaded {len(data)} keys from {self.namespace}")
            return data

        except InvalidToken:
            logger.error(f"Failed to decrypt {self.namespace_file}: invalid key")
            raise ValueError("Decryption failed: invalid master key")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse decrypted data: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading data from {self.namespace_file}: {e}")
            return {}

    async def _save_data(self, data: Dict[str, Any]) -> None:
        """
        Encrypt and save data to disk.
        """
        await self._ensure_initialized()

        try:
            json_data = json.dumps(data, indent=2)
            assert self._fernet is not None
            encrypted_data = self._fernet.encrypt(json_data.encode())

            temp_file = self.namespace_file.with_suffix(".tmp")
            async with await trio.open_file(temp_file, "wb") as f:
                await f.write(encrypted_data)

            temp_file.replace(self.namespace_file)

            logger.debug(f"Saved {len(data)} keys to {self.namespace}")

        except Exception as e:
            logger.error(f"Error saving data to {self.namespace_file}: {e}")
            raise

    async def _ensure_loaded(self) -> None:
        """Ensure cache is loaded from disk."""
        if not self._loaded:
            async with self._lock:
                if not self._loaded:
                    self._cache = await self._load_data()
                    self._loaded = True

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value by key.
        """
        await self._ensure_loaded()
        value = self._cache.get(key)

        if value is not None:
            logger.debug(f"KV get: {self.namespace}/{key} -> found")
        else:
            logger.debug(f"KV get: {self.namespace}/{key} -> not found")

        return value

    async def set(self, key: str, value: Any) -> None:
        """
        Set key-value pair.
        """
        await self._ensure_loaded()

        async with self._lock:
            self._cache[key] = value
            await self._save_data(self._cache)

        logger.debug(f"KV set: {self.namespace}/{key}")

    async def delete(self, key: str) -> bool:
        """
        Delete key-value pair.
        """
        await self._ensure_loaded()

        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                await self._save_data(self._cache)
                logger.debug(f"KV delete: {self.namespace}/{key} -> deleted")
                return True
            else:
                logger.debug(f"KV delete: {self.namespace}/{key} -> not found")
                return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists.
        """
        await self._ensure_loaded()
        return key in self._cache

    async def list_keys(self) -> List[str]:
        """
        List all keys in namespace.
        """
        await self._ensure_loaded()
        keys = list(self._cache.keys())
        logger.debug(f"KV list_keys: {self.namespace} -> {len(keys)} keys")
        return keys

    async def clear_namespace(self) -> None:
        """Clear all data in this namespace."""
        async with self._lock:
            self._cache.clear()
            await self._save_data(self._cache)

        logger.info(f"KV clear_namespace: {self.namespace}")

    async def get_all(self) -> Dict[str, Any]:
        """
        Get all key-value pairs in namespace.
        """
        await self._ensure_loaded()
        return dict(self._cache)

    async def update(self, data: Dict[str, Any]) -> None:
        """
        Update multiple key-value pairs at once.

        Args:
            data: Dictionary of key-value pairs to update
        """
        await self._ensure_loaded()

        async with self._lock:
            self._cache.update(data)
            await self._save_data(self._cache)

        logger.debug(f"KV update: {self.namespace} -> {len(data)} keys updated")

    async def size(self) -> int:
        """
        Get number of keys in namespace.
        """
        await self._ensure_loaded()
        return len(self._cache)

    def get_storage_path(self) -> Path:
        """
        Get path to encrypted storage file.
        """
        return self.namespace_file

    @staticmethod
    async def list_namespaces(agent_name: str, storage_dir: Optional[Path] = None) -> List[str]:
        """
        List all namespaces for an agent.
        """
        if storage_dir is None:
            storage_dir = Path("data") / "encrypted_store"

        agent_dir = storage_dir / agent_name

        if not agent_dir.exists():
            return []

        namespaces = []
        for file in agent_dir.glob("*.enc"):
            namespace = file.stem
            namespaces.append(namespace)

        logger.debug(f"Found {len(namespaces)} namespaces for agent {agent_name}")
        return namespaces

    @staticmethod
    async def delete_namespace(
        agent_name: str,
        namespace: str,
        storage_dir: Optional[Path] = None
    ) -> bool:
        """
        Completely delete a namespace file.
        """
        if storage_dir is None:
            storage_dir = Path("data") / "encrypted_store"

        namespace_file = storage_dir / agent_name / f"{namespace}.enc"

        if namespace_file.exists():
            namespace_file.unlink()
            logger.info(f"Deleted namespace: {agent_name}/{namespace}")
            return True
        else:
            logger.debug(f"Namespace not found: {agent_name}/{namespace}")
            return False
