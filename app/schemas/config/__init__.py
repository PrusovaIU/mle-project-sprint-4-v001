from pydantic_settings import BaseSettings
from .s3 import S3Settings
from .artifacts import ArtifactsSettings


class Settings(BaseSettings):
    s3: S3Settings
    artifacts: artifacts.ArtifactsSettings
