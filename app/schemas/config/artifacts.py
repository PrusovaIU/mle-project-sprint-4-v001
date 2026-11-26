from pathlib import Path

from pydantic import BaseModel, Field


class ArtifactsSettings(BaseModel):
    """Параметры артефактов для сервиса"""
    local_artifacts_dir: Path = Field(
        default="artifacts",
        description="Путь к директории, в которую будут сохранены "
                    "артефакты из S3"
    )
