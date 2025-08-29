from pathlib import Path

from loguru import logger


def init_keystore(key_folder: str) -> Path:
    """Create keystore if it does not exist."""
    key_path = Path(key_folder)
    if not key_path.exists():
        try:
            key_path.mkdir()
        except Exception as e:
            logger.error(f"Failed to create keystore {e}")
        logger.info("Keystore created")

    return key_path.absolute()
