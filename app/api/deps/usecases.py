from fastapi import Request, Depends
from app.usecases.recommendation import RecommendationUsecase
from typing import Annotated


def get_recommendation_usecase(request: Request) -> RecommendationUsecase:
    """
    :param request:
    :return: Экземпляр RecommendationUsecase.
    """
    return request.app.state.recommendation_service


RecommendUsecaseDep = Annotated[
    RecommendationUsecase,
    Depends(get_recommendation_usecase)
]
