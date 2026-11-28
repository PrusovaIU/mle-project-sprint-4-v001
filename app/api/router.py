from fastapi import APIRouter

from app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
)
from .deps.usecases import RecommendUsecaseDep


router = APIRouter(prefix="/recommendations", tags=["Рекомендации"])


@router.post(
    "",
    response_model=RecommendationResponse,
    summary="Получить рекомендации для пользователя",
)
async def recommend(
    payload: RecommendationRequest,
    usecase: RecommendUsecaseDep,
) -> RecommendationResponse:
    """
    Выдаёт рекомендации для пользователя.

    :param payload: Запрос.
    :param usecase: Usecase для выдачи рекомендаций.
    """
    recommendations = usecase.recommend(payload)
    is_cold_start = not recommendations or all(
        set(r.sources) <= {"popular"} for r in recommendations
    )
    return RecommendationResponse(
        user_id=payload.user_id,
        is_cold_start=is_cold_start,
        recommendations=recommendations,
    )
