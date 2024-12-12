import logging
import logging.config
from pathlib import Path

import yaml

server_logger = logging.getLogger("server")


def logging_setup():
    with open(Path("infrastructure", "configs", "logging.yaml"), "r") as f:
        logging_config = yaml.safe_load(f)
        logging.config.dictConfig(logging_config)
    server_logger.info("Logger was configured successfully")
