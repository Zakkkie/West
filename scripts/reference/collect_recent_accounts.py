"""CLI для загрузки свежих твитов и поиска аккаунтов с растущей популярностью.

Скрипт поддерживает два режима:

* **Боевой** — обращается к Twitter API v2 и требует `TWITTER_BEARER_TOKEN`.
* **Учебный** — читает заранее подготовленные JSON-файлы (см. `--demo-data`) и
  позволяет отработать пайплайн без доступа к Twitter.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import islice
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

import requests
from dotenv import load_dotenv

TWITTER_API_URL = "https://api.twitter.com/2/tweets/search/recent"


@dataclass
class AuthorMetrics:
    author_id: str
    username: str
    name: str
    followers: int
    following: int
    tweet_count: int
    listed_count: int
    account_created_at: str


@dataclass
class TrendingAccount:
    author: AuthorMetrics
    tweet_id: str
    text: str
    created_at: str
    like_count: int
    retweet_count: int
    reply_count: int
    quote_count: int

    @property
    def engagement(self) -> int:
        return self.like_count + self.retweet_count + self.reply_count + self.quote_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ищет свежие твиты от малых аккаунтов, которые быстро набирают вовлеченность."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/trending_accounts.csv"),
        help="Путь к CSV-файлу с результатами (по умолчанию data/processed/trending_accounts.csv).",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=3,
        help="Количество страниц по 100 твитов в каждой (max_results=100).",
    )
    parser.add_argument(
        "--min-engagement",
        type=int,
        default=50,
        help="Минимальная суммарная вовлеченность (лайки + ретвиты + ответы + цитаты).",
    )
    parser.add_argument(
        "--max-followers",
        type=int,
        default=10000,
        help="Максимальное число подписчиков для отбора аккаунтов.",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=os.getenv("DEFAULT_TWEET_LANGUAGE", "en"),
        help="Язык твитов для фильтра (например, en, ru).",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Дополнительные ключевые слова для поиска (например, стартап).",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=6,
        help="За сколько последних часов искать твиты (максимум 24).",
    )
    parser.add_argument(
        "--demo-data",
        type=Path,
        default=None,
        help=(
            "Путь к JSON-файлу с учебными данными. Позволяет выполнить все шаги "
            "без Twitter API."
        ),
    )
    return parser.parse_args()


def build_query(language: str, keywords: Optional[str]) -> str:
    base_filters = ["-is:retweet", "-is:reply", "-is:quote"]
    if language:
        base_filters.append(f"lang:{language}")
    if keywords:
        base_filters.append(keywords)
    return " ".join(base_filters)


def get_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def request_page(
    token: str,
    query: str,
    start_time: datetime,
    next_token: Optional[str],
) -> dict:
    params = {
        "query": query,
        "max_results": 100,
        "tweet.fields": "created_at,public_metrics,author_id",
        "expansions": "author_id",
        "user.fields": "created_at,public_metrics,username,name",
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sort_order": "relevancy",
    }
    if next_token:
        params["next_token"] = next_token
    response = requests.get(TWITTER_API_URL, headers=get_headers(token), params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def index_users(raw: dict) -> dict:
    users = raw.get("includes", {}).get("users", [])
    return {user["id"]: user for user in users}


def pick_trending_accounts(
    raw_tweets: Iterable[dict],
    users_index: dict,
    *,
    min_engagement: int,
    max_followers: int,
) -> List[TrendingAccount]:
    trending: List[TrendingAccount] = []
    for tweet in raw_tweets:
        author_id = tweet.get("author_id")
        user = users_index.get(author_id)
        if not user:
            continue
        metrics = user.get("public_metrics", {})
        followers = metrics.get("followers_count", 0)
        if followers > max_followers:
            continue
        tweet_metrics = tweet.get("public_metrics", {})
        account = TrendingAccount(
            author=AuthorMetrics(
                author_id=author_id,
                username=user.get("username", ""),
                name=user.get("name", ""),
                followers=followers,
                following=metrics.get("following_count", 0),
                tweet_count=metrics.get("tweet_count", 0),
                listed_count=metrics.get("listed_count", 0),
                account_created_at=user.get("created_at", ""),
            ),
            tweet_id=tweet.get("id", ""),
            text=tweet.get("text", ""),
            created_at=tweet.get("created_at", ""),
            like_count=tweet_metrics.get("like_count", 0),
            retweet_count=tweet_metrics.get("retweet_count", 0),
            reply_count=tweet_metrics.get("reply_count", 0),
            quote_count=tweet_metrics.get("quote_count", 0),
        )
        if account.engagement >= min_engagement:
            trending.append(account)
    return trending


def ensure_output_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, accounts: Iterable[TrendingAccount]) -> None:
    ensure_output_dir(path)
    fieldnames = [
        "tweet_id",
        "tweet_created_at",
        "tweet_text",
        "engagement",
        "like_count",
        "retweet_count",
        "reply_count",
        "quote_count",
        "author_id",
        "username",
        "name",
        "followers",
        "following",
        "tweet_count",
        "listed_count",
        "account_created_at",
        "collected_at",
    ]
    collected_at = datetime.now(timezone.utc).isoformat()
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for account in accounts:
            writer.writerow(
                {
                    "tweet_id": account.tweet_id,
                    "tweet_created_at": account.created_at,
                    "tweet_text": account.text.replace("\n", " ").strip(),
                    "engagement": account.engagement,
                    "like_count": account.like_count,
                    "retweet_count": account.retweet_count,
                    "reply_count": account.reply_count,
                    "quote_count": account.quote_count,
                    "author_id": account.author.author_id,
                    "username": account.author.username,
                    "name": account.author.name,
                    "followers": account.author.followers,
                    "following": account.author.following,
                    "tweet_count": account.author.tweet_count,
                    "listed_count": account.author.listed_count,
                    "account_created_at": account.author.account_created_at,
                    "collected_at": collected_at,
                }
            )


def load_demo_pages(path: Path) -> Iterator[dict]:
    """Загружает учебные данные из JSON-файла.

    Ожидается либо список страниц, либо один объект в формате Twitter API.
    """

    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    if isinstance(payload, list):
        for page in payload:
            if isinstance(page, dict):
                yield page
    elif isinstance(payload, dict):
        yield payload
    else:
        raise ValueError("Неверный формат demo-data: ожидается объект или список объектов.")


def collect_trending_accounts(args: argparse.Namespace) -> List[TrendingAccount]:
    if args.demo_data:
        pages = islice(load_demo_pages(args.demo_data), args.pages)
        trending: List[TrendingAccount] = []
        for data in pages:
            tweets = data.get("data", [])
            users = index_users(data)
            trending.extend(
                pick_trending_accounts(
                    tweets,
                    users,
                    min_engagement=args.min_engagement,
                    max_followers=args.max_followers,
                )
            )
        return trending

    load_dotenv()
    token = os.getenv("TWITTER_BEARER_TOKEN")
    if not token:
        raise RuntimeError(
            "Не найден TWITTER_BEARER_TOKEN. Создайте .env файл на основе .env.example или используйте --demo-data."
        )

    query = build_query(args.language, args.query)
    start_time = datetime.now(timezone.utc) - timedelta(hours=min(args.hours, 24))

    trending: List[TrendingAccount] = []
    next_token: Optional[str] = None

    for _ in range(args.pages):
        data = request_page(token, query, start_time, next_token)
        meta = data.get("meta", {})
        tweets = data.get("data", [])
        users = index_users(data)
        trending.extend(
            pick_trending_accounts(
                tweets,
                users,
                min_engagement=args.min_engagement,
                max_followers=args.max_followers,
            )
        )
        next_token = meta.get("next_token")
        if not next_token:
            break
    return trending


def main() -> None:
    args = parse_args()
    accounts = collect_trending_accounts(args)
    if not accounts:
        print("Не найдено аккаунтов, соответствующих критериям. Попробуйте снизить пороги.")
        return
    write_csv(args.output, accounts)
    print(f"Сохранено {len(accounts)} аккаунтов в {args.output}")


if __name__ == "__main__":
    main()
 
