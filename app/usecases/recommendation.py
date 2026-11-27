from loguru import logger
from dataclasses import dataclass, field
from app.utils.data_loader import DataLoader
from app.schemas.config.s3 import RecommendationsFilesSettings
from app.utils.similar import build_similar_score_map

import polars as pl


@dataclass
class _UserOfflineProfile:
    """Офлайн-профиль пользователя, собранный из рекомендаций."""

    als: dict[int, float] = field(default_factory=dict)
    i2i: dict[int, float] = field(default_factory=dict)
    ranked: dict[int, float] = field(default_factory=dict)


class RecommendationService:
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

