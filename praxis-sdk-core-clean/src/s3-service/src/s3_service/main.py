import re
import aioboto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
from loguru import logger

from s3_service.config import get_settings

settings = get_settings()


class S3Service:
    def __init__(self, bucket_name: str):
        if not re.match(r"^[a-z0-9.-]{3,63}$", bucket_name):
            raise ValueError(f"Invalid bucket name: {bucket_name}")
        self.s3_bucket_url = f"{settings.infrastructure.s3_base_url}/{settings.infrastructure.s3_bucket_prefix}-{bucket_name}"
        self.bucket_name = f"{settings.infrastructure.s3_bucket_prefix}-{bucket_name}"
        self.s3_client = None

    async def __aenter__(self):
        self.s3_client = (
            await aioboto3.Session()
            .client(
                "s3",
                endpoint_url=settings.infrastructure.s3_base_url,
                aws_access_key_id=settings.infrastructure.s3_access_key,
                aws_secret_access_key=settings.infrastructure.s3_secret_key,
            )
            .__aenter__()
        )
        await self._ensure_bucket_exists()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.s3_client:
            await self.s3_client.__aexit__(exc_type, exc_value, traceback)

    async def _ensure_bucket_exists(self):
        try:
            await self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.info(f"Bucket '{self.bucket_name}' does not exist. Creating bucket.")
                try:
                    await self.s3_client.create_bucket(Bucket=self.bucket_name)
                except ClientError as create_err:
                    logger.exception(f"Failed to create bucket '{self.bucket_name}'.")
                    raise Exception(f"Creation bucket error: {create_err}")
            else:
                logger.exception(f"Failed to access bucket '{self.bucket_name}'.")
                raise

    async def upload_file(self, file: UploadFile, file_key: str) -> str:
        try:
            await self.s3_client.upload_fileobj(
                file.file,
                self.bucket_name,
                file_key,
                ExtraArgs={"ACL": "public-read"},
            )
            return f"{self.s3_bucket_url}/{file_key}"
        except ClientError as e:
            logger.exception("Failed to upload file to S3.")
            raise Exception(f"Uploading file error: {e}")
        finally:
            await self.__aexit__(None, None, None)

    async def delete_file(self, file_key: str):
        try:
            await self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
        except ClientError as e:
            logger.exception("Failed to delete file from S3.")
            raise Exception(f"Deleting file error: {e}")
        finally:
            await self.__aexit__(None, None, None)

    def get_file_url(self, file_key: str) -> str:
        return f"{self.s3_bucket_url}/{file_key}"

    async def upload_file_bytes(
        self, file_key: str, file_bytes: bytes, content_type: str = None
    ) -> str:
        try:
            await self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_bytes,
                ContentType=content_type,
                ContentDisposition="inline",
                ACL="public-read",
            )
            return self.get_file_url(file_key)
        except ClientError as e:
            logger.exception("Failed to upload bytes to S3.")
            raise Exception(f"Uploading bytes error: {e}")
        finally:
            await self.__aexit__(None, None, None)

    async def list_files(self, prefix: str = "") -> list[str]:
        try:
            response = await self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            return [item["Key"] for item in response.get("Contents", [])]
        except ClientError as e:
            logger.exception("Failed to list files in S3 bucket.")
            raise Exception(f"Listing files error: {e}")
        finally:
            await self.__aexit__(None, None, None)

    async def get_file_bytes(self, file_key: str) -> bytes:
        try:
            response = await self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            return await response["Body"].read()
        except ClientError as e:
            logger.exception(f"Failed to get file bytes from S3 for key {file_key}.")
            raise Exception(f"Error getting file bytes: {e}")
        finally:
            await self.__aexit__(None, None, None)


async def get_s3_service(bucket_name: str) -> S3Service:
    async with S3Service(bucket_name) as service:
        return service


def s3_service_dependency(bucket_name: str):
    async def dependency() -> S3Service:
        async with S3Service(bucket_name) as service:
            return service

    return dependency
