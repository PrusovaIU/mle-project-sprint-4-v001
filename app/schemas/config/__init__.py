from pydantic_settings import BaseSettings
from .s3 import S3Settings


class Settings(BaseSettings):
    s3: S3Settings
