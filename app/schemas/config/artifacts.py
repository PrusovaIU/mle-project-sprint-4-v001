from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pathlib import Path


class ArtifactsSettings(BaseModel):
    """Параметры артефактов для сервиса"""
    local_artifacts_dir: Path = Field(
        default=Path("artifacts"),
        description="Путь к директории, в которую будут сохранены "
                    "артефакты из S3"
    )

    @field_validator("local_artifacts_dir")
    @classmethod
    def _create_local_artifacts_dir(cls, value: Path) -> Path:
        """Создаёт директорию (и все родительские), если её ещё нет."""
        value.mkdir(parents=True, exist_ok=True)
        return value
