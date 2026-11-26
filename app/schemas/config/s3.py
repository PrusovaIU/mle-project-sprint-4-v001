from pydantic import BaseModel, Field


class S3Settings(BaseModel):
    """Схема для параметров подключения к S3"""
    endpoint: str = Field(
        default="https://storage.yandexcloud.net",
        description="URL-адрес S3 хранилища"
    )
    access_key: str = Field(
        default="",
        description="Идентификатор ключа доступа"
    )
    secret_key: str = Field(
        default="",
        description="Секретный ключ доступа"
    )
    multipart_threshold: float = Field(
        default=32 * 1024**2,
        description="Порог размера файла, при превышении которого включается "
                    "multipart-загрузка"
    )
    multipart_chunksize: float = Field(
        default=32 * 1024**2,
        description="Размер одного чанка"
    )
    max_concurrency: float = Field(
        default=4,
        description="Максимально число параллельных потоков"
    )
    bucket: str = Field(
        default="mle-20261109-edf4b0c3eba4",
        description="Имя бакета в хранилище"
    )
    region: str = Field(
        default="ru-central1",
        description="Регион размещения хранилища"
    )
    rec_path: str = Field(
        default="recsys/recommendations",
        description="Путь к каталогу с рекомендациями внутри бакета"
    )
    data_path: str = Field(
        default="recsys/data",
        description="Путь к каталогу с данными внутри бакета"
    )
