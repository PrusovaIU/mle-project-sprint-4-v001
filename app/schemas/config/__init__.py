from pydantic_settings import BaseSettings, SettingsConfigDict
from .s3 import S3Settings
from .artifacts import ArtifactsSettings


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    s3: S3Settings
    artifacts: artifacts.ArtifactsSettings
