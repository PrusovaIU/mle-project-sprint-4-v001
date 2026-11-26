from pathlib import Path

import boto3
from boto3.s3.transfer import TransferConfig

from app.schemas.config.s3 import S3Settings


class S3Client:
    """
    Клиент для взаимодействия с S3

    :param config: Параметры подключения к S3.
    """
    def __init__(self, config: S3Settings) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=config.s3.endpoint,
            aws_access_key_id=config.s3.access_key,
            aws_secret_access_key=config.s3.secret_key,
            region_name=config.s3.region,
        )
        self._cfg = TransferConfig(
            multipart_threshold=config.multipart_threshold,
            multipart_chunksize=config.multipart_chunksize,
            max_concurrency=config.max_concurrency,
        )

    def download(self, s3_bucket: str, s3_key: str, local_path: Path) -> None:
        """
        Загрузка файла из S3.

        :param s3_bucket: Название бакета.
        :param s3_key: Ключ файла.
        :param local_path: Путь, куда будет сохранен файл.
        :return: None.
        """
        if local_path.exists():
            return
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._client.download_file(
            s3_bucket, s3_key, str(local_path), Config=self._cfg
        )
