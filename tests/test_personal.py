from __future__ import annotations

from app.schemas.recommendation import RecommendationRequest
import pytest
from app.usecases.recommendation import RecommendationUsecase


def test_offline_without_history(usecase: RecommendationUsecase):
    request = RecommendationRequest(user_id=1, history=[], limit=10)
    response = usecase.recommend(request)
    by_id = {r.track_id: r for r in response}

    assert {200, 201, 210, 211} <= set(by_id)

    # 200 — максимум ALS: score=1.0, источник есть
    assert by_id[200].als_score == pytest.approx(1.0)
    assert "als" in by_id[200].sources

    # 201 — минимум ALS: score=0.0, источника нет
    assert by_id[201].als_score == 0.0
    assert "als" not in by_id[201].sources

    # 210 — максимум offline_ranked: score=1.0
    assert by_id[210].i2i_score == 0.0  # i2i нет
    assert "offline_ranked" in by_id[210].sources

    # 211 — минимум offline_ranked: score=0.0
    assert "offline_ranked" not in by_id[211].sources

    # никаких отрицательных скоров — регрессия на баг из этого падения
    assert all(r.final_score >= 0.0 for r in response)
    assert all(r.als_score >= 0.0 for r in response)
    assert all(r.i2i_score >= 0.0 for r in response)
    assert all(r.popularity_score >= 0.0 for r in response)

    # i2i-канал не сработал (истории нет)
    assert all(r.i2i_score == 0.0 for r in response)


def test_no_negative_scores_for_partial_channel_coverage(
        usecase: RecommendationUsecase
):
    response = usecase.recommend(
        RecommendationRequest(user_id=1, history=[], limit=100)
    )
    for r in response:
        assert 0.0 <= r.final_score <= 1.05, r
        assert 0.0 <= r.als_score <= 1.0, r
        assert 0.0 <= r.i2i_score <= 1.0, r
        assert 0.0 <= r.popularity_score <= 1.0, r


def test_offline_ranking_prefers_higher_offline_score(
        usecase: RecommendationUsecase
):
    request = RecommendationRequest(
        user_id=1, history=[], limit=10, alpha=1.0
    )
    response = usecase.recommend(request)
    ids = [r.track_id for r in response]

    # 200 (als=0.9, rank1) должен быть выше 201 (als=0.5, rank2)
    assert ids.index(200) < ids.index(201)
