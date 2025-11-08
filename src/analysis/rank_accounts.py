"""Утилита для объединения выгрузок и расчёта рейтинга аккаунтов."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Агрегирует несколько CSV-файлов и строит рейтинг авторов."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Список CSV-файлов с выгрузками (например, data/processed/trending_accounts*.csv).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/ranked_accounts.csv"),
        help="Путь к файлу с итоговым рейтингом.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Сколько аккаунтов показать в итоговом рейтинге.",
    )
    return parser.parse_args()


def load_inputs(paths: Iterable[Path]) -> pd.DataFrame:
    """Загружает несколько CSV и сообщает, если какой-то файл отсутствует."""

    frames: List[pd.DataFrame] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Не найден файл {path}. Проверьте аргументы CLI.")
        frame = pd.read_csv(path)
        frames.append(frame)
    if not frames:
        raise ValueError("Не переданы входные CSV-файлы для ранжирования.")
    return pd.concat(frames, ignore_index=True)


def build_ranking(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["author_id", "username", "name"], as_index=False)
        .agg(
            tweets_observed=("tweet_id", "count"),
            avg_engagement=("engagement", "mean"),
            max_engagement=("engagement", "max"),
            median_followers=("followers", "median"),
        )
        .sort_values(by=["max_engagement", "avg_engagement"], ascending=[False, False])
    )
    return grouped


def main() -> None:
    args = parse_args()
    df = load_inputs(args.inputs)
    if df.empty:
        raise ValueError("Файлы без данных: убедитесь, что предварительно запущен сборщик.")
    ranking = build_ranking(df)
    top_frame = ranking.head(args.top)
    ensure_output_dir(args.output)
    top_frame.to_csv(args.output, index=False)
    print(top_frame)
    print(f"Итоговый рейтинг сохранён в {args.output}")


def ensure_output_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
