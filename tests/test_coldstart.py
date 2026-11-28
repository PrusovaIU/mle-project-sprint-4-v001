from __future__ import annotations

from app.schemas.recommendation import (
    HistoryItem,
    RecommendationRequest,
)
from app.usecases.recommendation import RecommendationUsecase
import pytest


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


def test_cold_start_with_history_uses_i2i_but_no_offline(usecase):
    request = RecommendationRequest(
        user_id=999,
        history=[HistoryItem(track_id=500)],
        limit=10,
    )
    response = usecase.recommend(request)
    by_id = {r.track_id: r for r in response}

    # оба трека в выдаче
    assert {600, 601} <= set(by_id)

    # 600 — максимум i2i: score=1.0, источник есть
    assert by_id[600].i2i_score == pytest.approx(1.0)
    assert "i2i" in by_id[600].sources

    # 601 — минимум i2i: score=0.0, источника нет
    assert by_id[601].i2i_score == 0.0
    assert "i2i" not in by_id[601].sources

    # офлайн-каналов нет ни у кого
    for tid in (600, 601):
        assert by_id[tid].als_score == 0.0
        assert "offline_ranked" not in by_id[tid].sources
