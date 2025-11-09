"""Utility checks to help diagnose common setup issues.

This script is intentionally lightweight so it can be executed even if the main
collector CLI is broken. It focuses on two problems that repeatedly show up in
support conversations:

* running the project from a directory that is not a real Git checkout, which
  prevents commands such as ``git checkout -- …`` from working;
* accidentally overwriting ``collect_recent_accounts.py`` with shell snippets
  (for example when applying patches manually), which leads to ``IndentationError``
  before the CLI even starts.

Run the script with ``python scripts/doctor.py`` from the project root. It will
print actionable guidance for any issues that it detects. The script exits with
status code 0 when everything looks fine, or 1 otherwise so that it can be used
in automated diagnostics.

Pass ``--restore-collector`` to rewrite ``collect_recent_accounts.py`` with the
known-good reference copy bundled in ``scripts/reference``. This option is
useful for users who downloaded the project as a ZIP archive and therefore
cannot rely on ``git checkout`` to repair the file.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from textwrap import dedent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR_PATH = PROJECT_ROOT / "src" / "data_collection" / "collect_recent_accounts.py"
REFERENCE_COLLECTOR_PATH = PROJECT_ROOT / "scripts" / "reference" / "collect_recent_accounts.py"


def check_git_checkout() -> list[str]:
    """Verify that the project root contains a Git repository."""
    git_dir = PROJECT_ROOT / ".git"
    if git_dir.exists() and git_dir.is_dir():
        return []

    return [
        "Папка проекта не выглядит как клон Git: не найден каталог .git.",
        "Если вы скачивали архив ZIP, скачайте репозиторий повторно командой",
        "    git clone <URL>",
        "или инициализируйте Git в текущей папке перед попыткой `git checkout`.",
    ]


def check_collector_header() -> list[str]:
    """Ensure that the collector file starts with a docstring, not shell code."""
    if not COLLECTOR_PATH.exists():
        return [
            "Не найден файл src/data_collection/collect_recent_accounts.py.",
            "Убедитесь, что вы запускаете скрипт из корня проекта West.",
        ]

    try:
        first_line = COLLECTOR_PATH.read_text(encoding="utf-8").splitlines()[0]
    except Exception as exc:  # pragma: no cover - extremely unlikely
        return [
            "Не удалось прочитать collect_recent_accounts.py:",
            f"    {exc}",
        ]

    if first_line.lstrip().startswith("\""):
        return []

    return [
        "collect_recent_accounts.py не начинается со строкового литерала.",
        "Кажется, файл был перезаписан инструкцией вида",
        "    (cd \"$(git rev-parse --show-toplevel)\" && git apply --3way <<'EOF'",
        "Восстановите файл из репозитория Git или скопируйте свежую версию",
        "из архива релиза.",
    ]


def restore_collector() -> list[str]:
    """Copy the known-good collector implementation into place."""

    if not REFERENCE_COLLECTOR_PATH.exists():
        return [
            "Не найден эталонный collect_recent_accounts.py в scripts/reference.",
            "Обновите репозиторий до последней версии и повторите попытку.",
        ]

    COLLECTOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REFERENCE_COLLECTOR_PATH, COLLECTOR_PATH)

    return [
        "collect_recent_accounts.py восстановлен из scripts/reference.",
        "Запустите команду повторно, чтобы убедиться, что ошибка исчезла.",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--restore-collector",
        action="store_true",
        help="перезаписать collect_recent_accounts.py эталонной версией",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.restore_collector:
        messages = restore_collector()
        print("\n".join(messages))
        # Continue with diagnostics afterwards so the user immediately sees the
        # updated status.

    issues: list[str] = []
    issues.extend(check_git_checkout())
    issues.extend(check_collector_header())

    if not issues:
        print("Похоже, что структура проекта в порядке. Можно запускать CLI.")
        return 0

    print("Обнаружены проблемы с окружением:\n")
    print(dedent("\n".join(issues)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
