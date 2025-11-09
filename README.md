# West

Этот проект содержит утилиты для поиска перспективных Twitter‑аккаунтов по
свежим твитам и формирования рейтинга по вовлечённости.

## Как запустить сборщик аккаунтов

Ниже описан полный путь от подготовки окружения до запуска скрипта в учебном и
боевом режимах. Все команды приводятся для PowerShell (Windows). На Linux и
macOS их можно запускать в терминале, заменив `python` на `python3`, если это
необходимо.

### 1. Склонируйте репозиторий

```powershell
git clone https://github.com/<ВАШ-АККАУНТ>/West.git
cd West
```

Если при запуске `git` получаете сообщение, что команда не найдена —
установите Git с официального сайта и перезапустите PowerShell.

### 2. Создайте и активируйте виртуальное окружение

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
```

Если PowerShell сообщает, что запуск скриптов запрещён, выполните команду
`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`, закройте
окно и откройте новое.

### 3. Установите зависимости

```powershell
pip install -r requirements.txt
```

Убедитесь, что слева от приглашения командной строки отображается префикс
`(.venv)`. Если его нет, активируйте окружение повторно.

### 4. Настройте переменные окружения (опционально)

Скопируйте файл `.env.example` в `.env` и укажите в нём значение
`TWITTER_BEARER_TOKEN`, если планируете работать с реальным API. Можно также
изменить язык по умолчанию через `DEFAULT_TWEET_LANGUAGE` (например, `ru`).

### 5. Запустите скрипт

**Учебный режим без API:**

```powershell
python src/data_collection/collect_recent_accounts.py `
    --demo-data data/raw/sample_recent_tweets.json `
    --min-engagement 30
```

Команда читает подготовленный JSON-файл, фильтрует аккаунты и сохраняет CSV по
пути `data/processed/trending_accounts.csv`. Обратный апостроф (`` ` ``) в конце
строки — символ переноса в PowerShell.

**Боевой режим с Twitter API:**

```powershell
python src/data_collection/collect_recent_accounts.py `
    --query "startup" `
    --language ru `
    --hours 12 `
    --min-engagement 40 `
    --pages 5
```

Скрипт подтянет свежие твиты через Twitter API и сформирует CSV с тем же
именем, что и в учебном режиме. Изменяйте параметры `--query`, `--language`,
`--hours`, `--min-engagement`, `--pages`, чтобы адаптировать фильтры.

Если видите ошибку `RuntimeError: TWITTER_BEARER_TOKEN is required`, убедитесь,
что переменная указана в `.env` и файл лежит в корне проекта.

### 6. Проверьте результат

Откройте `data/processed/trending_accounts.csv` в Excel, LibreOffice или
просмотрите его в терминале командой `type data\processed\trending_accounts.csv`
(`cat` на Linux/macOS). Если файл пустой, уменьшите значение
`--min-engagement` или увеличьте `--pages`.

## Анализ нескольких выгрузок

После нескольких запусков сборщика можно построить рейтинг аккаунтов:

```powershell
python src/analysis/rank_accounts.py data/processed/trending_accounts*.csv --top 20
```

Результат сохранится в `data/processed/ranked_accounts.csv`.
