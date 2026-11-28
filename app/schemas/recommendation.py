from typing import Literal

from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    """Один элемент истории прослушиваний пользователя."""

    track_id: int = Field(description="ID трека")
    listened_at: str | None = Field(
        default=None,
        description="ISO-строка времени прослушивания",
    )


class RecommendationRequest(BaseModel):
    """Запрос на рекомендации."""
    user_id: int = Field(description="ID пользователя")
    history: list[HistoryItem] = Field(
        default_factory=list,
        description="Список track_id, которые пользователь слушал недавно "
                    "(для онлайн-части)",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Количество рекомендаций",
    )
    alpha: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Вес офлайн-кандидатов (personal ALS) при смешивании. "
                    "Вес онлайн (i2i) = 1 - alpha.",
    )


class RecommendedTrack(BaseModel):
    """Рекомендованный трек с источниками и итоговым скором."""

    track_id: int
    final_score: float = Field(description="Итоговый нормализованный скор")
    als_score: float = Field(
        default=0.0,
        description="Скор из personal ALS"
    )
    i2i_score: float = Field(
        default=0.0,
        description="Скор из i2i (similar)"
    )
    popularity_score: float = Field(
        default=0.0,
        description="Нормализованная популярность (top_popular)"
    )
    sources: list[Literal["als", "i2i", "popular", "offline_ranked"]] = Field(
        default_factory=list,
        description="Из каких каналов пришёл трек",
    )


class RecommendationResponse(BaseModel):
    """Ответ сервиса."""

    user_id: int
    is_cold_start: bool = Field(
        description="True, если у пользователя нет офлайн-профиля "
                    "и/или истории"
    )
    recommendations: list[RecommendedTrack]
