
# 🛠️ `praxis-config`: Centralized Configuration & Logging for Praxis Infrastructure

This package provides centralized configuration management, secure credential handling, and structured logging for Praxis-based services and agents.

---

## 📦 Features

* ✅ Centralized `.env`-driven configuration using `pydantic-settings`
* 🔒 Secure handling of secrets (e.g., Fernet keys, API credentials)
* 🌐 Support for PostgreSQL, Redis, Kafka, Qdrant, S3, and more
* 🔧 Configs for AI services, LiveKit, Telegram, Twitter, etc.
* 🧠 Prompt enum definitions for prompt-to-name mappings
* 📊 Structured logging via `structlog`

---

## 📁 Module Overview

### 🔐 `Settings`

Main application config composed of:

* `InfrastructureConfig`: PostgreSQL, Redis, Qdrant, S3, Kafka, Langfuse, etc.
* `TelegramAppSetupServiceConfig`: Endpoints for Telegram App setup API.
* `DeployService`: Configuration for the internal Deploy Service.
* Twitter, OpenAI, Anthropic, Heygen, and LiveKit credentials
* Constants for agent action intervals (posting, commenting, liking, etc.)
* `ai_registry_url`: Helper to build full AI Registry endpoint

### 🌍 `ServerSettings`

Environment-specific settings for service integrations:

* `CoingeckoSettings`
* `RedisSettings`
* `HyperLiquidSettings`

### 🔐 `Fernet` Encryption

`cipher = Fernet(get_settings().infrastructure.fernet_key)`
Used for secure encryption/decryption operations in memory.

### 🧾 `configure_logging()`

Structured logging setup with `structlog`.
Supports timestamping, exception rendering, context merging, and pretty output.

### 🧠 `PromptMapper`

Enum that maps prompt types to their prompt template strings (from `infrastructure.prompts.tokens`).

---

## 🔧 Usage

```python
from praxis_config import get_settings, configure_logging, get_logger

settings = get_settings()
configure_logging()
logger = get_logger()

logger.info("Service started", service="twitter-agent")
```

Access specific config fields:

```python
dsn = settings.infrastructure.postgres_dsn
qdrant_url = settings.infrastructure.qdrant_url
redis_dsn = settings.infrastructure.redis_dsn
```

Use the `Fernet` cipher:

```python
from praxis_config import cipher

encrypted = cipher.encrypt(b"secret")
decrypted = cipher.decrypt(encrypted)
```

---

## 📁 Environment Variables

This package loads from a `.env` file (or environment directly). Key variables include:

* `POSTGRES_HOST`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET`
* `CREATIVITY_API_ID`, `CREATIVITY_API_KEY`
* `COINGECKO_API_KEY`, `COINGECKO_API_URL`
* `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
* `HYPERLIQUD_API_URL`
* Others (Twitter, OpenAI, LiveKit, etc.)

---

## 🧪 Development

Make sure to install dependencies:

```bash
pip install -r requirements.txt
```

Or if using uv:

```bash
uv sync
```

---

## 🔐 Security Note

Do **not** commit your actual `.env` file to version control. Sensitive credentials (API keys, secrets) should be managed via environment injection or a secure secrets manager.

---

## 📄 License

MIT License. See `LICENSE` for details.
