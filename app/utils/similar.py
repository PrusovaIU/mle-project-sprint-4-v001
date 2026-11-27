import polars as pl


def build_similar_map(
    similar_df: pl.DataFrame,
    max_per_track: int = 20,
) -> dict[int, list[int]]:
    """
    Построение словаря {track_id: [similar_id, ...]} из датафрейма similar.

    :param similar_df: DataFrame с колонками track_id, similar_id, rank.
    :param max_per_track: Ограничение числа похожих на трек.
    :return: Словарь похожих треков.
    """
    trimmed = (
        similar_df.filter(pl.col("rank") <= max_per_track)
        .sort(["track_id", "rank"])
        .group_by("track_id")
        .agg(pl.col("similar_id").alias("similar"))
    )
    return dict(
        zip(
            trimmed["track_id"].to_list(),
            trimmed["similar"].to_list(),
        )
    )


def build_similar_score_map(
    similar_df: pl.DataFrame,
    max_per_track: int = 20,
) -> dict[int, list[tuple[int, float]]]:
    """
    Формирование словаря {track_id: [(similar_id, score), ...]}.

    :param similar_df: DataFrame с колонками track_id, similar_id, score, rank.
    :param max_per_track: Ограничение числа похожих на трек.
    :return: Словарь похожих треков со скорами.
    """
    trimmed = (
        similar_df.filter(pl.col("rank") <= max_per_track)
        .sort(["track_id", "rank"])
        .group_by("track_id")
        .agg(
            pl.col("similar_id").alias("similar"),
            pl.col("score").alias("scores"),
        )
    )
    return {
        tid: list(zip(sim, sc))
        for tid, sim, sc in zip(
            trimmed["track_id"].to_list(),
            trimmed["similar"].to_list(),
            trimmed["scores"].to_list(),
        )
    }


def index_by_user(df: pl.DataFrame, key: str = "user_id") -> dict:
    """
    Индексация строки DataFrame по значениям указанной колонки.

    Группировка DataFrame по колонке `key` с возвращением словаря, где каждому
    уникальному значению ключа соответствует словарь с остальными колонками
    строки.

    :param df: Входной DataFrame для индексации.
    :param key: Имя колонки, по значениям которой строится индекс.

    :return: Словарь вида `{key_value: {column_name: value, ...}}`, где
        ключами служат значения колонки `key`.
    """
    grouped = df.group_by(key).agg(pl.all().exclude(key))
    return dict(zip(grouped[key].to_list(), grouped.iter_rows(named=True)))
