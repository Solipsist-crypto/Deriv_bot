# 🚀 Deriv_bot

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Railway](https://img.shields.io/badge/Railway-Deployed-0B0D0E?logo=railway&logoColor=white)](https://railway.app/)
[![Deriv API](https://img.shields.io/badge/Deriv-REST%20%26%20WebSocket-FF444F)](https://api.deriv.com/)
**Deriv_bot** — асинхронний автоматизований торговий бот для платформи Deriv. Він отримує ринкові свічки в реальному часі, обчислює технічні індикатори, формує торгові сигнали, відкриває і контролює угоди та зберігає повну історію у PostgreSQL.

Проєкт повністю розгорнуто в хмарі на **Railway**. Налаштовано автоматичний деплой при пуші в гілку `main`, тому зміни в репозиторії одразу проходять pipeline Railway і публікуються як оновлення сервісу.

> ⚠️ Бот торгує коштами лише за налаштованими акаунтами та параметрами. Завжди проводьте тестування на демонстраційному акаунті і пам’ятайте про ризики автоматизованої торгівлі.

---

## 📌 About

### Основні можливості

- 🔌 Підключення до Deriv через REST API та WebSocket.
- 📈 Аналіз свічок по кількох валютних парах і золоту.
- 📊 Комбінована стратегія на основі RSI, EMA, MACD і Bollinger Bands.
- 🛡️ Захист від входу у флєт через ADX та від погоні за ціною через відстань до EMA 50.
- ⚡ Динамічна експірація угод на основі ATR-перцентиля.
- 🧠 Збір ML-фічей і навчальний XGBoost-pipeline для майбутнього ML-фільтра.
- 💾 Збереження угод, індикаторів, параметрів угоди та результату в PostgreSQL.
- 🤖 Telegram-сповіщення про входи, виходи та помилки.
- 📱 Команда `/stats` у Telegram для перегляду балансу, Win Rate і кількості угод.
- 🔁 Асинхронне виконання, повторні спроби ордерів і фонове відстеження угод.

---

## 🧰 Tech Stack

| Технологія | Призначення |
|---|---|
| **Python 3.10+** | Основна логіка застосунку та асинхронний runtime |
| **asyncio / aiohttp** | Асинхронні мережеві операції та REST-запити |
| **WebSockets** | Отримання свічок і управління угодами Deriv |
| **Pandas / NumPy** | Обробка ринкових даних і побудова ознак |
| **TA-Lib-style `ta`** | RSI, EMA, MACD, Bollinger Bands та ATR |
| **XGBoost / scikit-learn** | Навчання моделі й оцінка прогнозів на історії угод |
| **PostgreSQL / asyncpg** | Історія угод та дані для ML-навчання |
| **Telegram Bot API / aiogram** | Моніторинг і доступ до статистики |
| **Railway** | Хмарний хостинг і безперервний деплой |
| **GitHub** | Вихідний код і запуск CI/CD-процесу через Railway |

---

## 🧠 Як у проєкті використовується ШІ та Machine Learning

ШІ використовується як додатковий рівень прийняття рішень поверх класичної індикаторної стратегії. Кожна угода перетворюється на структурований набір ознак, а код ML-модуля навчає модель оцінювати ймовірність успішного результату.

### Потік даних для ML

1. Бот отримує останні свічки для активів з `SYMBOLS`.
2. `MultiIndicatorStrategy` обчислює RSI, EMA fast/slow, MACD, Bollinger Bands, ATR і ADX.
3. Додатково формується контекст угоди:
   - відстань ціни до EMA;
   - ширина і положення всередині Bollinger Bands;
   - нахил RSI;
   - ATR-перцентиль;
   - сила тренду ADX;
   - година і день тижня;
   - дискретні BUY/SELL-сигнали та кількість голосів індикаторів.
4. Результат угоди з `win`, профітом і technical signal записується в PostgreSQL.
5. `export_dataset.py` експортує історію в `trades_dataset.csv`.
6. `train_model.py` робить часовий train/test split і навчає `XGBClassifier`.
7. Після навчання XGBoost використовує time-series split, балансування класів і ROC-AUC для оцінки моделі.
8. Поріг моделі оптимізується за очікуваною прибутковістю (EV), а артефакти зберігаються в `xgb_model.pkl`, `model_features.pkl` і `best_threshold.pkl`.

### Поточний режим

Наразі бот знаходиться в режимі збору даних для ML v3:

- модель XGBoost навчається локально з історії угод;
- усі основні технічні ознаки зберігаються в БД;
- ML-фільтр тимчасово вимкнений;
- поки збирається реальна вибірка, кожен дозволений стратегією сигнал приймається з умовною ймовірністю `100%`.

Після накопичення достатньо репрезентативної вибірки ML-модуль може автоматично відхиляти слабкі сигнали нижче окремого порогу ймовірності. Поточна заглушка в `ml_filter.py` не використовує справжню ML-прогнозну модель.

---

## 🏗️ Architecture & Deployment

```text
GitHub push → Railway build → Cloud process
                                      │
                                      ├── Deriv REST API
                                      ├── Deriv WebSocket
                                      ├── Indicator & ML pipeline
                                      ├── PostgreSQL history
                                      └── Telegram notifications
```

### Робочий цикл

1. `main.py` запускає асинхронний сервіс.
2. `AccountManager` авторизується через Deriv REST API.
3. `MarketManager` отримує свічки через WebSocket.
4. `MultiIndicatorStrategy` обчислює ознаки та голоси індикаторів.
5. `MLFilter` перевіряє сигнал; у поточній версії це режим збору даних.
6. `TraderManager` надсилає proposal, відкриває контракт і чекає результат.
7. `DatabaseManager` зберігає угоду в PostgreSQL.
8. `TelegramNotifier` повідомляє про кожен ключовий етап.

### CI/CD

- Джерелом деплою є гілка `main`.
- Репозиторій підключений до Railway.
- Кожен `push` у `main` запускає автоматичний build і deploy Railway.
- Railway перезапускає застосунок після успішного розгортання.
- Змінні середовища зберігаються у Railway Variables, а не в Git.
- PostgreSQL підключається через змінну `DATABASE_URL`.

---

## 📁 Структура проєкту

| Файл | Опис |
|---|---|
| `main.py` | Головний цикл сканування, асинхронні задачі та orchestration |
| `account.py` | Авторизація Deriv і отримання WebSocket OTP URL |
| `market.py` | Отримання історичних свічок через Deriv WebSocket |
| `strategy.py` | RSI, EMA, MACD, Bollinger Bands, ATR, ADX і сформування сигналу |
| `trader.py` | Створення контракту, динамічна експірація та перевірка результату |
| `database.py` | Підключення до PostgreSQL і запис/читання угод |
| `ml_filter.py` | Поточний режим-заглушка ML-фільтра |
| `train_model.py` | Навчання XGBoost і оптимізація порогу за EV |
| `export_dataset.py` | Експорт історії PostgreSQL у CSV для навчання |
| `tg_bot.py` | Telegram-сповіщення та команда `/stats` |
| `config.py` | Читання змінних оточення |
| `requirements.txt` | Python-залежності |

---

## 🚀 Getting Started

### Вимоги

- Python 3.10+
- акаунт Deriv і персональний access token;
- PostgreSQL;
- Telegram Bot API;
- Railway для хмарного розгортання.

### Локальний запуск

```bash
git clone https://github.com/Solipsist-crypto/Deriv_bot.git
cd Deriv_bot

python -m venv venv
```

#### Windows

```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy NUL .env
python main.py
```

#### Linux / macOS

```bash
source venv/bin/activate
pip install -r requirements.txt
touch .env
python main.py
```

### Змінні оточення

Створіть `.env` локально або додайте змінні в Railway Variables:

```env
PAT_TOKEN=your_deriv_personal_access_token
APP_ID=your_deriv_app_id
DATABASE_URL=postgresql://user:password@host:port/database
TG_BOT_TOKEN=your_telegram_bot_token
TG_CHAT_ID=your_telegram_chat_id
```

Не додавайте `.env`, токени або приватні database credentials у GitHub.

### Навчання ML-моделі

```bash
# Експортувати історію угод з налаштованого PostgreSQL
python export_dataset.py

# Навчити XGBoost-модель за часовим розбиттям
python train_model.py
```

Модель очікує датасет `trades_dataset.csv` і після навчання створює артефакти моделі у корені проєкту.

### Деплой на Railway

1. Створіть або підключіть проєкт у Railway.
2. Додайте PostgreSQL service.
3. Підключіть репозиторій `Solipsist-crypto/Deriv_bot`.
4. Додайте всі змінні оточення з розділу вище.
5. Зв’яжіть PostgreSQL-змінну `DATABASE_URL` із Railway Variables.
6. Виконайте push у гілку `main`.
7. Railway автоматично збере та запустить нову версію бота.

---

## ⚙️ Основні параметри

| Параметр | Поточне значення |
|---|---:|
| Активи | XAU/USD, EUR/USD, GBP/USD, USD/JPY, AUD/USD |
| Таймфрейм свічок | 15 хвилин |
| Інтервал сканування | 5 хвилин |
| Базова ставка | 5 USD |
| Базова експірація | 15 хвилин |
| Низька волатильність ATR | 45 хвилин |
| Середня волатильність ATR | 15 хвилин |
| Висока волатильність ATR | 30 хвилин |
| Стартове значення ML-порогу | 55% |
| Мінімум ADX для входу | 20 |

---

## 👤 Author

Створено **[Solipsist-crypto](https://github.com/Solipsist-crypto)**.
