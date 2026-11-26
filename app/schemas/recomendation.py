from typing import Optional
from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    """Схема для запроса рекомендации"""
    user_id: int = Field(
        description="Идентификатор пользователя"
    )
    history: Optional[list[int]] = Field(
        default=None,
        description="Список track_id, которые пользователь слушал недавно "
                    "(для онлайн-части)"
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Количество рекомендаций"
    )
    exclude_track_ids: Optional[list[int]] = Field(
        default=None,
        description="Треки, которые нужно исключить "
                    "(например, уже прослушанные)"
    )


class RecommendationItem(BaseModel):
    """Схема для рекомендуемого трека"""
    track_id: int = Field(
        description="ID рекомендуемого трека"
    )
    score: float = Field(
        description="Оценка релевантности трека для пользователя"
    )
    rank: int = Field(
        description="Позиция трека в списке рекомендаций (1 - верхняя)"
    )
    source: str = Field(
        description="Источник: 'offline' | 'online_i2i' | "
                    "'top_popular' | 'mixed'"
    )


class RecommendationResponse(BaseModel):
    """Схема ответа сервиса с рекомендацией"""
    user_id: int = Field(
        description="ID пользователя, для которого предоставлена рекомендация"
    )
    recommendations: list[RecommendationItem] = Field(
        description="Список рекомендуемых треков"
    )
    meta: dict = Field(
        default_factory=dict,
        description="Дополнительная информация"
    )

