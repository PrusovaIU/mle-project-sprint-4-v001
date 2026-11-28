from __future__ import annotations

from app.schemas.recommendation import (
    HistoryItem,
    RecommendationRequest,
)
from app.usecases.recommendation import RecommendationUsecase


def test_cold_start_returns_popular_only(usecase: RecommendationUsecase):
    request = RecommendationRequest(user_id=999, history=[], limit=10)

    response = usecase.recommend(request)
    ids = [r.track_id for r in response]

    # все популярные треки присутствуют
    assert set(ids) == {100, 101, 102, 103}
    # отсортированы по убыванию final_score
    scores = [r.final_score for r in response]
    assert scores == sorted(scores, reverse=True)
    # у каждого трека источник "popular"
    for r in response:
        assert "popular" in r.sources
        assert r.popularity_score > 0



