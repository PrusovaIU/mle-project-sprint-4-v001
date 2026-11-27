from pydantic import BaseModel, Field, computed_field, model_validator


class MultipartSettings(BaseModel):
    """Параметры multipart-загрузки"""
    threshold: float = Field(
        default=32 * 1024**2,
        description="Порог размера файла, при превышении которого включается "
                    "multipart-загрузка"
    )
    chunk_size: float = Field(
        default=32 * 1024**2,
        description="Размер одного чанка"
    )
    max_concurrency: float = Field(
        default=4,
        description="Максимально число параллельных потоков"
    )


class RecommendationsFilesSettings(BaseModel):
    """Пути к файлам с рекомендациями в S3"""
    dir: str = Field(
        default="/recsys/recommendations/",
        description="Путь к директории с файлами рекомендаций"
    )
    top_popular_file: str = Field(
        default="top_popular.parquet",
        description="Название файла с топом треков"
    )
    personal_als_file: str = Field(
        default="personal_als.parquet",
        description="Название файла с персональными ALS рекомендациями"
    )
    similar_file: str = Field(
        default="similar.parquet",
        description="Название файла со списком похожих треков"
    )
    recommendations_file: str = Field(
        default="recommendations.parquet",
        description="Название файла со списком рекомендаций"
    )

    _files: dict[str, str] | None = None

    def _build_path(self, filename: str) -> str:
        """Собирает полный путь из директории и имени файла."""
        return f"{self.dir.rstrip('/')}/{filename}"

    @model_validator(mode="after")
    def _fill_files(self) -> "RecommendationsFilesSettings":
        """Заполняет _files путями для каждого файла."""
        self._files = {
            self.top_popular_file: self._build_path(self.top_popular_file),
            self.personal_als_file: self._build_path(self.personal_als_file),
            self.similar_file: self._build_path(self.similar_file),
            self.recommendations_file:
                self._build_path(self.recommendations_file),
        }
        return self

    @computed_field
    @property
    def files(self) -> dict[str, str]:
        return self._files



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
    multipart: MultipartSettings = Field(
        default_factory=MultipartSettings,
        description="Параметры multipart-загрузки"
    )
    bucket: str = Field(
        default="mle-20261109-edf4b0c3eba4",
        description="Имя бакета в хранилище"
    )
    region: str = Field(
        default="ru-central1",
        description="Регион размещения хранилища"
    )
    recsys: RecommendationsFilesSettings = Field(
        default_factory=RecommendationsFilesSettings,
        description="Ключи для файлов с рекомендациями"
    )
