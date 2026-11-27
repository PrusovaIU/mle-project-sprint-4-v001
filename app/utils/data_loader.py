from pathlib import Path
from typing import Any

import polars as pl

from app.schemas.config import Settings
from app.services.s3_client import S3Client


class DataLoader:
    """Загрузчик артефактов, необходимых для инференса."""

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
        """
        Загрузка файлов с рекомендациями из S3 и кэширование.

        :return: None.
        """
        for file_name, file_key in self._config.s3.recsys.files.items():
            local_path = self._download_parquet(file_key, file_name)
            self._cache[file_name] = pl.read_parquet(local_path)

    def get(self, file_name: str) -> pl.DataFrame:
        """Получить загруженный датафрейм по имени файла."""
        if file_name not in self._cache:
            raise KeyError(
                f"Файл {file_name!r} не загружен. "
                f"Сначала вызовите load_all_recommendations()."
            )
        return self._cache[file_name]
