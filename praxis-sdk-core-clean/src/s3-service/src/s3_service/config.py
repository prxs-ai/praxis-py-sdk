from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    s3_bucket_prefix: str = "praxis"
    s3_region: str = Field(validation_alias="S3_REGION")
    s3_access_key: str = Field(validation_alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(validation_alias="S3_SECRET")

    @property
    def s3_base_url(self):
        return f"https://{self.s3_region}.digitaloceanspaces.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
