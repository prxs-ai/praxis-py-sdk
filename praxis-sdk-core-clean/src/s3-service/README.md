# Async S3 Service

An asynchronous  client for interacting with S3-compatible storage using `aioboto3`. Designed for integration with FastAPI-based projects and supports file uploads, downloads, and management.

## Installation

### Using [Poetry](https://-poetry.org/)

```toml
[tool.poetry.dependencies]
 = "^3.11"
fastapi = ">=0.115.8,<0.116.0"
aioboto3 = ">=12.2.0,<13.0.0"
loguru = ">=0.7.2,<0.8.0"
```

Then run:


```
poetry install
```

### Or using pip

```
pip install fastapi aioboto3 loguru
```

## Dependencies

* `aioboto3` — for asynchronous S3 operations
* `loguru` — for logging
* `fastapi` — for UploadFile type and integration (optional)

## Configuration

The module expects a configuration available at:

```
from s3_service.config import get_settings
```

Example structure:

```
class Settings:
    class Infrastructure:
        s3_base_url: str = "https://s3.example.com"
        s3_access_key: str = "your_access_key"
        s3_secret_key: str = "your_secret_key"
        s3_bucket_prefix: str = "your-prefix"
    
    infrastructure: Infrastructure = Infrastructure()

def get_settings() -> Settings:
    return Settings()
```

## Usage

```
import asyncio
from fastapi import UploadFile
from your_module_path import S3Service

async def main():
    async with S3Service("my-bucket") as service:
        # Upload a file
        file = UploadFile(filename="test.txt", file=io.BytesIO(b"test content"))
        url = await service.upload_file(file, "test.txt")
        print(f"File uploaded to: {url}")

        # Get file bytes
        content = await service.get_file_bytes("test.txt")
        print(f"File content: {content}")

asyncio.run(main())
```

### Method: `upload_file`

Uploads a file from FastAPI's UploadFile object.

```
await service.upload_file(file: UploadFile, file_key: str) -> str
```

Returns: Public URL of the uploaded file

### Method: `upload_file_bytes`

Uploads raw bytes as a file.

```
await service.upload_file_bytes(file_key: str, file_bytes: bytes, content_type: str = None) -> str
```

Returns: Public URL of the uploaded file

### Method: `get_file_bytes`

Downloads a file as bytes.

```
await service.get_file_bytes(file_key: str) -> bytes
```

### Method: `delete_file`

Deletes a file from the bucket.

```
await service.delete_file(file_key: str)
```

### Method: `list_files`

Lists all files in the bucket (optionally filtered by prefix).

```
await service.list_files(prefix: str = "") -> list[str]
```

### Method: `get_file_url`

Generates public URL for a file (without downloading it).

```
service.get_file_url(file_key: str) -> str
```

## Integration with FastAPI

The client is designed to be used as a FastAPI dependency:

```
from fastapi import Depends

@app.post("/upload")
async def upload_file(
    file: UploadFile,
    service: S3Service = Depends(s3_service_dependency("my-bucket"))
):
    url = await service.upload_file(file, file.filename)
    return {"url": url}
```

## Bucket Naming

The service automatically prepends the configured prefix to all bucket names. For example, if your prefix is `dev` and you request bucket `images`, the actual bucket name will be `dev-images`.

## Error Handling

All methods raise exceptions with descriptive messages when S3 operations fail. The service includes automatic bucket creation if it doesn't exist when first accessed.

## License

MIT License