from __future__ import annotations

from app.schemas.recommendation import (
    HistoryItem,
    RecommendationRequest,
)
import pytest


def test_personal_plus_history_merges_channels(usecase):
    request = RecommendationRequest(
        user_id=2,
        history=[HistoryItem(track_id=500), HistoryItem(track_id=501)],
        limit=10,
    )
    response = usecase.recommend(request)
    by_id = {r.track_id: r for r in response}

    assert {300, 301, 310, 311} <= set(by_id)
    assert {600, 601, 602} <= set(by_id)

    assert by_id[300].als_score == pytest.approx(1.0)
    assert "als" in by_id[300].sources
    assert by_id[301].als_score == 0.0
    assert "als" not in by_id[301].sources

    assert "offline_ranked" in by_id[310].sources
    assert "offline_ranked" not in by_id[311].sources

    assert by_id[600].i2i_score == pytest.approx(1.0)
    assert "i2i" in by_id[600].sources

    assert 0.0 < by_id[601].i2i_score < 1.0
    assert "i2i" in by_id[601].sources

    assert by_id[602].i2i_score == 0.0
    assert "i2i" not in by_id[602].sources

    # инвариант контракта для каналов, у которых есть поле в схеме
    for r in response:
        assert ("als" in r.sources) is (r.als_score > 0), r
        assert ("i2i" in r.sources) is (r.i2i_score > 0), r
        assert ("popular" in r.sources) is (r.popularity_score > 0), r

    # скоры неотрицательны (регрессия на final_score=-0.225)
    assert all(r.final_score >= 0.0 for r in response)
    assert all(r.als_score >= 0.0 for r in response)
    assert all(r.i2i_score >= 0.0 for r in response)
    assert all(r.popularity_score >= 0.0 for r in response)


def test_history_tracks_excluded(usecase):
    history = [HistoryItem(track_id=500), HistoryItem(track_id=501)]
    request = RecommendationRequest(user_id=2, history=history, limit=10)
    response = usecase.recommend(request)
    ids = {r.track_id for r in response}
    assert 500 not in ids and 501 not in ids


def test_alpha_controls_channel_weight(usecase):
    history = [HistoryItem(track_id=500)]

    online = usecase.recommend(
        RecommendationRequest(user_id=2, history=history, alpha=0.0, limit=10)
    )
    offline = usecase.recommend(
        RecommendationRequest(user_id=2, history=history, alpha=1.0, limit=10)
    )

    online_ids = [r.track_id for r in online]
    offline_ids = [r.track_id for r in offline]

    # при alpha=0 i2i-трек должен быть выше офлайн-трека
    assert online_ids.index(600) < online_ids.index(300)
    # при alpha=1 — наоборот
    assert offline_ids.index(300) < offline_ids.index(600)


def test_limit_respected(usecase):
    request = RecommendationRequest(
        user_id=2,
        history=[HistoryItem(track_id=500)],
        limit=2,
    )
    response = usecase.recommend(request)
    assert len(response) <= 2
