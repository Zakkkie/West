# Пошаговый учебный план

Ниже описан минимальный цикл работы с проектом по отслеживанию перспективных Twitter-аккаунтов.

## 1. Подготовка окружения
1. Установите Python 3.10+.
2. Склонируйте репозиторий и перейдите в папку `West`.
3. Создайте и активируйте виртуальное окружение:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```
4. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
5. Если у вас есть токен, создайте файл `.env` на основе `.env.example` и укажите `TWITTER_BEARER_TOKEN`. Без токена можно выполнять учебный режим с `--demo-data`.

## 2. Сбор данных
### Вариант А. Учебные данные
1. Убедитесь, что файл `data/raw/sample_recent_tweets.json` на месте.
2. Запустите скрипт в учебном режиме:
   ```bash
   python src/data_collection/collect_recent_accounts.py \
     --demo-data data/raw/sample_recent_tweets.json \
     --min-engagement 30
   ```
3. Откройте `data/processed/trending_accounts.csv` и посмотрите, какие аккаунты попали в выборку.

### Вариант Б. Реальные данные (требуется токен)
1. Убедитесь, что переменная `TWITTER_BEARER_TOKEN` задана в `.env`.
2. Запустите сборщик:
   ```bash
   python src/data_collection/collect_recent_accounts.py --query "startup" --min-engagement 30
   ```
3. Проверьте, что появился файл `data/processed/trending_accounts.csv`.
4. Экспериментируйте с параметрами `--max-followers`, `--hours`, `--language` и `--pages`.

## 3. Аналитика
1. После нескольких запусков сохраните CSV-файлы с разными именами (например, через параметр `--output`).
2. Объедините выгрузки и постройте рейтинг:
   ```bash
   python src/analysis/rank_accounts.py data/processed/trending_accounts*.csv
   ```
3. Изучите таблицу в консоли и файл `data/processed/ranked_accounts.csv`. Если увидите ошибку о пустых файлах, вернитесь к шагу 2 и соберите данные.

## 4. Расширение проекта
* Добавьте ноутбук в папку `notebooks/` для визуализаций.
* Подключите дополнительные источники (например, новости, Reddit).
* Настройте планировщик задач (cron, GitHub Actions) для регулярного запуска.
