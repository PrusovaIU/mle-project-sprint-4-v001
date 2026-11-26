from app.services.s3_client import S3Client
from app.schemas.config import Settings
from typing import Any
from pathlib import Path
import polars as pl


class DataLoader:
    """Загрузчик артефактов, необходимые для инференса."""

    def __init__(self, config: Settings) -> None:
        self._config = config
        self._s3 = S3Client(config.s3)
        self._cache: dict[str, Any] = {}

    def _download_parquet(self, s3_key: str, local_filename: str) -> Path:
        """
        Загрузка файла `parquet` из S3.

        :param s3_key: Ключ файла в S3.
        :param local_filename: Имя файла для сохранения.
        :return: Локальный путь к скаченному файлу.
        """
        local = self._config.artifacts.local_artifacts_dir / local_filename
        self._s3.download(s3_key, local)
        return local

    def load_all_recommendations(self) -> None:
        for file_name, file_key in self._config.s3.recs.files.items():
            local_path = self._download_parquet(file_key, file_name)
            self._cache[file_name] = pl.read_parquet(local_path)
