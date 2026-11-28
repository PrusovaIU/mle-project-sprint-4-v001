from __future__ import annotations

import pytest
import polars as pl

from app.schemas.config.s3 import RecommendationsFilesSettings
from app.usecases.recommendation import RecommendationUsecase


class FakeDataLoader:
    """DataLoader-заглушка: отдаёт заранее подготовленные DataFrame."""

    def __init__(self, frames: dict[str, pl.DataFrame]) -> None:
        self._frames = frames

    def get(self, file_name: str) -> pl.DataFrame:
        return self._frames[file_name]


@pytest.fixture
def recsys_settings() -> RecommendationsFilesSettings:
    return RecommendationsFilesSettings()


@pytest.fixture
def frames() -> dict[str, pl.DataFrame]:
    """
    Артефакты:
      * user 1 — есть ALS и offline_ranked, без истории;
      * user 2 — есть ALS и offline_ranked, есть история;
      * user 999 — отсутствует (cold-start).
    """
    top_popular = pl.DataFrame(
        {
            "track_id": [100, 101, 102, 103],
            "score": [100.0, 50.0, 25.0, 12.5],
        }
    )
    personal_als = pl.DataFrame(
        {
            "user_id": [1, 1, 2, 2],
            "track_id": [200, 201, 300, 301],
            "score": [0.9, 0.5, 0.8, 0.4],
            "rank": [1, 2, 1, 2],
        }
    )
    recommendations = pl.DataFrame(
        {
            "user_id": [1, 1, 2, 2],
            "track_id": [210, 211, 310, 311],
            "final_score": [0.7, 0.3, 0.6, 0.2],
            "rank": [1, 2, 1, 2],
        }
    )
    similar = pl.DataFrame(
        {
            "track_id": [500, 500, 501],
            "similar_id": [600, 601, 602],
            "score": [0.95, 0.85, 0.75],
            "rank": [1, 2, 1],
        }
    )
    return {
        "top_popular.parquet": top_popular,
        "personal_als.parquet": personal_als,
        "recommendations.parquet": recommendations,
        "similar.parquet": similar,
    }


@pytest.fixture
def usecase(frames, recsys_settings) -> RecommendationUsecase:
    uc = RecommendationUsecase(FakeDataLoader(frames), recsys_settings)
    uc.initialize()
    return uc
