from loguru import logger
from collections import defaultdict
from app.utils.data_loader import DataLoader
from app.schemas.config.s3 import RecommendationsFilesSettings
from app.utils.similar import build_similar_score_map
from app.schemas import recommendation as recs_schemas
from typing import Callable

import polars as pl


class RecommendationUsecase:
    """
    Сервис выдачи рекомендаций.

    Смешивает:
      * офлайн-кандидатов (personal_als + offline recommendations);
      * онлайн-кандидатов (i2i по свежей истории пользователя);
      * популярность как fallback / добавку для cold-start.

    :param data_loader: Загрузчик данных.
    :param recsys_settings: Настройки с путями до файлов в S3.
    """

    def __init__(
            self,
            data_loader: DataLoader,
            recsys_settings: RecommendationsFilesSettings
    ) -> None:
        self._loaded: bool = False
        self._loader = data_loader
        self._recsys_settings = recsys_settings

        # офлайн
        self._als_by_user: dict[int, dict[int, float]] = {}
        self._offline_ranked_by_user: dict[int, dict[int, float]] = {}
        self._top_popular: list[tuple[int, float]] = []

        # i2i
        self._similar: dict[int, list[tuple[int, float]]] = {}

    def check_inited(self) -> None:
        """Проверка, что сервис инициализирован."""
        if not self._loaded:
            raise RuntimeError("RecommendationService.initialize() не вызван")

    def initialize(self) -> None:
        """
        Инициализация экземпляра: построение всех in-memory индексов.
        Вызывается на старте приложения.
        """
        if self._loaded:
            return
        logger.info("Loading artifacts into RecommendationService...")
        self._build_offline_indices()
        self._build_similar_index()
        self._loaded = True
        logger.info(
            f"RecommendationService ready:\n"
            f"\tusers_als={len(self._als_by_user)},\n"
            f"\tusers_ranked={len(self._offline_ranked_by_user)},\n"
            f"\tpopular={len(self._top_popular)},\n"
            f"\tsimilar_tracks={len(self._similar)}"
        )

    def _build_offline_indices(self) -> None:
        """
        Загрузка данных с рекомендациями.

        :return: None.
        """
        # personal_als: user_id, track_id, score, rank
        als_df = self._loader.get(self._recsys_settings.personal_als_file)
        als_df = als_df.sort(["user_id", "rank"])
        self._als_by_user = self._rows_to_scored_dict(als_df, "score")

        # recommendations: user_id, track_id, final_score, rank
        rec_df = self._loader.get(self._recsys_settings.recommendations_file)
        rec_df = rec_df.sort(["user_id", "rank"])
        self._offline_ranked_by_user = self._rows_to_scored_dict(
            rec_df, "final_score"
        )

        # top_popular: score уже агрегированный; нормализуем
        top_df = self._loader.get(self._recsys_settings.top_popular_file)
        top_df = top_df.sort("score", descending=True)
        max_score = float(top_df["score"].max() or 1.0) or 1.0
        self._top_popular = [
            (int(t), float(s) / max_score)
            for t, s in zip(
                top_df["track_id"].to_list(),
                top_df["score"].to_list(),
            )
        ]

    @staticmethod
    def _rows_to_scored_dict(
            df: pl.DataFrame, score_col: str
    ) -> dict[int, dict[int, float]]:
        """
        Преобразование строк DataFrame в вложенный словарь с оценками.

        :param df: Входной DataFrame, содержащий колонки `user_id`, `track_id`
            и `score_col`.

        :param score_col: Имя колонки с оценками, значения которой будут
            приведены к `float`.

        :return: Вложенный словарь вида `{user_id: {track_id: score}}`, где
            ключи и оценки приведены к `int` и `float` соответственно.
        """
        result: dict[int, dict[int, float]] = {}
        for uid, tids, scores in zip(
            df["user_id"].to_list(),
            df["track_id"].to_list(),
            df[score_col].to_list(),
        ):
            result.setdefault(int(uid), {})[int(tids)] = float(scores)
        return result

    def _build_similar_index(self, max_per_track: int = 20) -> None:
        """
        Построение индекса похожих треков на основе данных, загруженных через
        loader.

        :param max_per_track: Количество похожих на трек.
        :return: None
        """
        similar_df = self._loader.get(self._recsys_settings.similar_file)
        self._similar = build_similar_score_map(
            similar_df,
            max_per_track=max_per_track
        )

    def recommend(
            self,
            request: recs_schemas.RecommendationRequest
    ) -> list[recs_schemas.RecommendedTrack]:
        """
        Формирование рекомендаций для пользователя.

        :param request: Запрос.
        :return: Список рекомендаций длиной не более `request.limit`.
        """
        self.check_inited()

        user_id = request.user_id
        history_ids = [item.track_id for item in request.history]
        history_set = set(history_ids)

        candidates = self._build_candidates(user_id, history_ids, history_set)
        scored = self._score_candidates(
            candidates, alpha=request.alpha, exclude=history_set
        )
        return self._top_n(scored, request.limit)

    def _build_candidates(
            self,
            user_id: int,
            history_ids: list[int],
            history_set: set[int],
    ) -> dict:
        """
        Формирование словаря кандидатов для пользователя путём объединения
        нескольких источников.

        :param user_id: Идентификатор пользователя, для которого строятся
            кандидаты.

        :param history_ids: Список идентификаторов треков из истории
            пользователя.

        :param history_set: Множество идентификаторов треков из истории для
            быстрой проверки вхождения.

        :return: Словарь кандидатов вида
            `{track_id: {source_name: score, ...}}`,
            где ключи — идентификаторы треков.
        """
        als = self._als_by_user.get(user_id, {})
        ranked = self._offline_ranked_by_user.get(user_id, {})
        i2i_scores = self._compute_i2i_scores(history_ids, history_set)

        candidates = self._merge_candidates(als, ranked, i2i_scores)

        if not candidates:
            candidates = {t: {"popular": s} for t, s in self._top_popular}

        return candidates

    def _compute_i2i_scores(
            self,
            history_ids: list[int],
            history_set: set[int],
            window: int = 10,
    ) -> dict[int, float]:
        """
        Онлайн i2i-скоры по последним `window` трекам истории.

        Для каждого похожего трека берётся максимум по сходству,
        чтобы избежать раздувания счёта от повторов.

        :param history_ids: Список идентификаторов треков из истории
            пользователя.

        :param history_set: Множество идентификаторов треков из истории для
            быстрой проверки вхождения.

        :param window: Количество последних треков истории, учитываемых при
            расчёте.

        :return: Словарь i2i-оценок вида `{track_id: score}`, где
            значение — максимальная оценка схожести для трека.
        """
        i2i_scores: dict[int, float] = defaultdict(float)
        for t in history_ids[-window:]:
            for sim_t, sim_s in self._similar.get(t, []):
                if sim_t == t or sim_t in history_set:
                    continue
                i2i_scores[sim_t] = max(i2i_scores[sim_t], float(sim_s))
        return i2i_scores

    @staticmethod
    def _merge_candidates(
            als: dict[int, float],
            ranked: dict[int, float],
            i2i: dict[int, float],
    ) -> dict[int, dict[str, float]]:
        """
        Объединение источников в {track_id: {source: score}}.

        :param als: Словарь ALS-оценок вида `{track_id: score}`.

        :param ranked: Словарь оценок офлайн-ранжирования вида `
            {track_id: score}`.

        :param i2i: Словарь i2i-оценок вида `{track_id: score}`.

        :return: Словарь вида `{track_id: {source_name: score, ...}}`,
            где `source_name` — один из `"als"`, `"offline_ranked"`, `"i2i"`.
        """
        pool: dict[int, dict[str, float]] = defaultdict(dict)

        for t, s in als.items():
            pool[t]["als"] = float(s)
        for t, s in ranked.items():
            pool[t]["offline_ranked"] = float(s)
        for t, s in i2i.items():
            pool[t]["i2i"] = float(s)
        return pool

    @staticmethod
    def _top_n(
            scored: list[recs_schemas.RecommendedTrack],
            limit: int,
    ) -> list[recs_schemas.RecommendedTrack]:
        """
        Сортирует по `final_score` и отдаёт не более `limit` элементов.

        :param scored: Список рекомендаций для сортировки и обрезки.

        :param limit: Максимальное количество элементов в результирующем
            списке.

        :return: Отсортированный по убыванию `final_score` список рекомендаций,
            содержащий не более `limit` элементов.
        """
        scored.sort(key=lambda x: x.final_score, reverse=True)
        return scored[:limit]

    def _score_candidates(
            self,
            pool: dict[int, dict[str, float]],
            alpha: float,
            exclude: set[int],
    ) -> list[recs_schemas.RecommendedTrack]:
        """
        Подсчет итогового скора.

        Формула:
            base = alpha * offline_signal + (1 - alpha) * i2i_signal
            offline_signal = weighted(als, offline_ranked)
            final = base + POPULARITY_BOOST * popularity (если трек популярен)

        :param pool: Словарь кандидатов вида
            `{track_id: {source_name: score, ...}}`.

        :param alpha: Вес офлайн-сигнала в формуле итогового скора
            (в диапазоне от 0 до 1).

        :param exclude: Множество идентификаторов треков, которые нужно
            исключить из результата.

        :return: Список рекомендаций `RecommendedTrack` с рассчитанными
            итоговыми скорами.
        """
        normalizers = {
            "als": _minmax([v["als"] for v in pool.values() if "als" in v]),
            "i2i": _minmax([v["i2i"] for v in pool.values() if "i2i" in v]),
            "offline_ranked": _minmax(
                [v["offline_ranked"] for v in pool.values() if
                 "offline_ranked" in v]
            ),
        }
        popularity_map = dict(self._top_popular)

        return [
            self._score_track(t, sources, alpha, popularity_map, normalizers)
            for t, sources in pool.items()
            if t not in exclude
        ]

    def _score_track(
            self,
            track_id: int,
            sources: dict[str, float],
            alpha: float,
            popularity_map: dict[int, float],
            normalizers: dict[str, Callable[[float], float]],
    ) -> recs_schemas.RecommendedTrack:
        """
        Подсчет итогового скора для одного трека.

        :param track_id: Идентификатор трека, для которого считается скор.

        :param sources: Словарь исходных оценок трека по источникам вида
            `{source_name: score}`.

        :param alpha: Вес офлайн-сигнала при объединении оценок
            (в диапазоне от 0 до 1).

        :param popularity_map: Словарь популярности треков вида
            `{track_id: popularity_score}`.

        :param normalizers: Словарь функций min-max нормализации по источникам
            вида `{source_name: normalizer}`.

        :return: RecommendedTrack с итоговым и покомпонентными скорами, а
            также списком источников.
        """
        als_s = normalizers["als"](sources.get("als", 0.0))
        ranked_s = normalizers["offline_ranked"](
            sources.get("offline_ranked", 0.0))
        i2i_s = normalizers["i2i"](sources.get("i2i", 0.0))
        pop_s = popularity_map.get(track_id, 0.0)

        final = self._combine_scores(als_s, ranked_s, i2i_s, pop_s, alpha)

        return recs_schemas.RecommendedTrack(
            track_id=int(track_id),
            final_score=round(float(final), 6),
            als_score=round(float(als_s), 6),
            i2i_score=round(float(i2i_s), 6),
            popularity_score=round(float(pop_s), 6),
            sources=self._collect_sources(sources, pop_s),
        )

    @staticmethod
    def _combine_scores(
            als_s: float,
            ranked_s: float,
            i2i_s: float,
            pop_s: float,
            alpha: float,
    ) -> float:
        """
        Объединение нормализованных сигналов в единый итоговый скор трека.

        :param als_s: Нормализованная оценка ALS-сигнала.

        :param ranked_s: Нормализованная оценка офлайн-ранжирования.

        :param i2i_s: Нормализованная i2i-оценка.

        :param pop_s: Нормализованная оценка популярности трека.

        :param alpha: Вес офлайн-сигнала при смешивании с i2i
            (в диапазоне от 0 до 1).

        :return: Итоговый скор трека.
        """
        offline_s = 0.5 * als_s + 0.5 * ranked_s
        base = alpha * offline_s + (1.0 - alpha) * i2i_s
        return base + 0.05 * pop_s

    @staticmethod
    def _collect_sources(
            sources: dict[str, float],
            pop_s: float,
    ) -> list[str]:
        """
        Формирование списка источников, из которых трек попал в кандидаты.

        :param sources: Словарь оценок трека по источникам вида
            `{source_name: score}`.

        :param pop_s: Скор популярности трека; при значении больше 0
            добавляется источник `"popular"`.

        :return: Список названий источников трека.
        """
        srcs = list(sources.keys())
        if pop_s > 0 and "popular" not in srcs:
            srcs.append("popular")
        return srcs


def _minmax(values: list[float]):
    """
    Возвращает функцию нормализации. Если все значения равны или пусты —
    возвращает константу 0.0, чтобы не делить на ноль.
    """
    if not values:
        return lambda _x: 0.0
    lo = min(values)
    hi = max(values)
    if hi <= lo:
        return lambda _x: 0.0
    span = hi - lo
    return lambda x: (float(x) - lo) / span
