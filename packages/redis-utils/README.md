# Redis Post Delay Manager

###Async utility to enforce delays between user posts using Redis.

## Installation

```
pip install aioredis loguru
```

## Dependencies
- `aioredis` (v2.x)
- `loguru` (v0.7.x)

## Usage

```
from redis_delay import ensure_delay_between_posts

await ensure_delay_between_posts(username="test_user", delay=300)  # 5 min delay
```

### Features
- Enforces minimum delay between user posts
- Random default delay (5-10 minutes) if none specified
- Async Redis operations
- Automatic data decoding
- Detailed logging

## Configuration
Requires Redis client configured in `redis_client/main.py` with:
- `get_redis_db()` function
- `Post` dataclass

## License
MIT
