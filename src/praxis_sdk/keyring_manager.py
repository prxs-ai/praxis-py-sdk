import os
from typing import Optional, Dict, Any
from loguru import logger

try:
    import keyring
    from keyring.errors import KeyringError
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logger.warning("keyring package not available.")


class KeyringManager:
    """Manages secure credential storage using system keyring."""

    SERVICE_NAME = "praxis-agent"

    def __init__(self, service_name: Optional[str] = None):
        """
        Initialize keyring manager.

        Args:
            service_name: Custom service name for keyring storage (default: "praxis-agent")
        """
        self.service_name = service_name or self.SERVICE_NAME
        self.available = KEYRING_AVAILABLE

        if not self.available:
            logger.warning("Keyring not available. Credentials will fall back to environment variables.")
        else:
            try:
                keyring.get_keyring()
                logger.info(f"Keyring initialized: {keyring.get_keyring().__class__.__name__}")
            except Exception as e:
                logger.warning(f"Keyring initialization failed: {e}. Falling back to environment variables.")
                self.available = False

    def set_credential(self, key: str, value: str) -> bool:
        """
        Store a credential in the system keyring.

        Args:
            key: Credential key/identifier
            value: Credential value to store

        Returns:
            True if stored successfully, False otherwise
        """
        if not self.available:
            logger.warning(f"Keyring not available. Cannot store credential: {key}")
            return False

        try:
            keyring.set_password(self.service_name, key, value)
            logger.info(f"Credential stored in keyring: {key}")
            return True
        except KeyringError as e:
            logger.error(f"Failed to store credential {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error storing credential {key}: {e}")
            return False

    def get_credential(self, key: str, fallback_env: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a credential from the system keyring with environment variable fallback.

        Args:
            key: Credential key/identifier
            fallback_env: Environment variable name to check if keyring fails

        Returns:
            Credential value or None if not found
        """
        if self.available:
            try:
                value = keyring.get_password(self.service_name, key)
                if value:
                    logger.debug(f"Retrieved credential from keyring: {key}")
                    return value
            except KeyringError as e:
                logger.warning(f"Failed to retrieve credential {key} from keyring: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error retrieving credential {key}: {e}")

        if fallback_env:
            env_value = os.getenv(fallback_env)
            if env_value:
                logger.debug(f"Retrieved credential from environment: {fallback_env}")
                return env_value

        env_value = os.getenv(key)
        if env_value:
            logger.debug(f"Retrieved credential from environment: {key}")
            return env_value

        logger.warning(f"Credential not found: {key}")
        return None

    def delete_credential(self, key: str) -> bool:
        """
        Delete a credential from the system keyring.

        Args:
            key: Credential key/identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.available:
            logger.warning(f"Keyring not available. Cannot delete credential: {key}")
            return False

        try:
            keyring.delete_password(self.service_name, key)
            logger.info(f"Credential deleted from keyring: {key}")
            return True
        except KeyringError as e:
            logger.error(f"Failed to delete credential {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting credential {key}: {e}")
            return False

    def list_credentials(self) -> Dict[str, bool]:
        """
        List all known credential keys and their availability.

        Returns:
            Dictionary mapping credential keys to availability status
        """
        known_keys = [
            "OPENAI_API_KEY",
            "API_KEY",
            "NOISE_KEY",
            "TLS_CERT_PATH",
            "TLS_KEY_PATH",
        ]

        status = {}
        for key in known_keys:
            value = self.get_credential(key)
            status[key] = value is not None

        return status

    def migrate_from_env(self, keys: Optional[list[str]] = None) -> Dict[str, bool]:
        """
        Migrate credentials from environment variables to keyring.

        Args:
            keys: List of environment variable names to migrate (default: common keys)

        Returns:
            Dictionary mapping keys to migration success status
        """
        if keys is None:
            keys = [
                "OPENAI_API_KEY",
                "API_KEY",
            ]

        results = {}
        for key in keys:
            env_value = os.getenv(key)
            if env_value:
                success = self.set_credential(key, env_value)
                results[key] = success
                if success:
                    logger.info(f"Migrated {key} to keyring")
            else:
                results[key] = False
                logger.debug(f"No environment variable found for {key}")

        return results

    def get_api_key(self, provider: str = "openai") -> Optional[str]:
        """
        Convenience method to get API key for a specific provider.

        Args:
            provider: Provider name (e.g., "openai", "anthropic")

        Returns:
            API key or None
        """
        key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }

        key = key_map.get(provider.lower())
        if not key:
            logger.warning(f"Unknown provider: {provider}")
            return None

        return self.get_credential(key)


_keyring_manager: Optional[KeyringManager] = None


def get_keyring_manager(service_name: Optional[str] = None) -> KeyringManager:
    """
    Get or create the global keyring manager instance.

    Args:
        service_name: Custom service name (default: "praxis-agent")

    Returns:
        KeyringManager instance
    """
    global _keyring_manager
    if _keyring_manager is None:
        _keyring_manager = KeyringManager(service_name)
    return _keyring_manager
