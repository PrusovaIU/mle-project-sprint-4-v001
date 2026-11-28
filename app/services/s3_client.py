from pathlib import Path

import boto3
from boto3.s3.transfer import TransferConfig

from app.schemas.config.s3 import S3Settings
from loguru import logger


class S3Client:
    """
    Клиент для взаимодействия с S3.

    :param config: Параметры подключения к S3.
    """

    def __init__(self, config: S3Settings) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=config.endpoint,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            region_name=config.region,
        )
        self._cfg = TransferConfig(
            multipart_threshold=config.multipart.threshold,
            multipart_chunksize=config.multipart.chunk_size,
            max_concurrency=config.multipart.max_concurrency
        )
        self._bucket = config.bucket

    def download(self, s3_key: str, local_path: Path) -> None:
        """
        Загрузка файла из S3.

        :param s3_key: Ключ файла.
        :param local_path: Путь, куда будет сохранен файл.
        :return: None.
        """
        if local_path.exists():
            logger.info(f"Файл {local_path.absolute()} загружен ранее")
            return
        local_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(
            f"Загрузка объекта: bucket={self._bucket}; key={s3_key}..."
        )
        self._client.download_file(
            self._bucket,
            s3_key.lstrip("/"),
            str(local_path),
            Config=self._cfg
        )
