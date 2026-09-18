# Deriv ML Trading Bot

Асинхронний торговий бот для платформи Deriv. Створений для автоматизованої торгівлі та збору ML-датасету (15-хвилинний таймфрейм).

## Функціонал
* Сканування ринку за індикаторами RSI, EMA Cross та Bollinger Bands.
* Відкриття угод через WebSocket API.
* Запис історії торгів та зрізу індикаторів у базу PostgreSQL.
* Telegram-бот для моніторингу статусу угод та виведення статистики (/stats).

## Налаштування середовища
Створіть файл `.env` та вкажіть наступні змінні:
\`\`\`env
PAT_TOKEN=ваш_токен_deriv
APP_ID=ваш_app_id
DATABASE_URL=postgresql://user:password@host:port/db_name
TG_BOT_TOKEN=токен_телеграм_бота
TG_CHAT_ID=ваш_чат_id
\`\`\`

## Запуск
\`\`\`bash
pip install -r requirements.txt
python main.py
\`\`\`