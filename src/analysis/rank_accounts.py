"""Утилита для объединения выгрузок и расчёта рейтинга аккаунтов."""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Dict, Iterable, List, Tuple


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


def load_inputs(paths: Iterable[Path]) -> List[dict]:
    """Загружает несколько CSV и сообщает, если какой-то файл отсутствует."""

    rows: List[dict] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Не найден файл {path}. Проверьте аргументы CLI.")
        with path.open(encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rows.append(row)
    if not rows:
        raise ValueError("Не переданы входные CSV-файлы для ранжирования.")
    return rows


def build_ranking(rows: List[dict]) -> List[dict]:
    grouped: Dict[Tuple[str, str, str], Dict[str, List[int]]] = defaultdict(
        lambda: {"engagement": [], "followers": [], "tweet_ids": []}
    )
    for row in rows:
        author_id = row.get("author_id", "")
        username = row.get("username", "")
        name = row.get("name", "")
        key = (author_id, username, name)
        try:
            engagement = int(float(row.get("engagement", 0)))
        except ValueError:
            engagement = 0
        try:
            followers = int(float(row.get("followers", 0)))
        except ValueError:
            followers = 0
        grouped[key]["engagement"].append(engagement)
        grouped[key]["followers"].append(followers)
        grouped[key]["tweet_ids"].append(row.get("tweet_id", ""))

    ranking: List[dict] = []
    for (author_id, username, name), metrics in grouped.items():
        engagements = metrics["engagement"]
        followers = metrics["followers"]
        ranking.append(
            {
                "author_id": author_id,
                "username": username,
                "name": name,
                "tweets_observed": len(metrics["tweet_ids"]),
                "avg_engagement": round(mean(engagements), 2) if engagements else 0,
                "max_engagement": max(engagements) if engagements else 0,
                "median_followers": int(median(followers)) if followers else 0,
            }
        )

    ranking.sort(
        key=lambda row: (row["max_engagement"], row["avg_engagement"]),
        reverse=True,
    )
    return ranking


def write_output(path: Path, rows: List[dict]) -> None:
    ensure_output_dir(path)
    fieldnames = [
        "author_id",
        "username",
        "name",
        "tweets_observed",
        "avg_engagement",
        "max_engagement",
        "median_followers",
    ]
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def print_preview(rows: List[dict]) -> None:
    for row in rows:
        print(
            f"@{row['username']:<20} | max={row['max_engagement']:<4} | "
            f"avg={row['avg_engagement']:<5} | tweets={row['tweets_observed']:<3} | "
            f"median_followers={row['median_followers']}"
        )


def main() -> None:
    args = parse_args()
    rows = load_inputs(args.inputs)
    ranking = build_ranking(rows)
    top_rows = ranking[: args.top]
    if not top_rows:
        raise ValueError("Файлы без данных: убедитесь, что предварительно запущен сборщик.")
    write_output(args.output, top_rows)
    print_preview(top_rows)
    print(f"Итоговый рейтинг сохранён в {args.output}")


def ensure_output_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
