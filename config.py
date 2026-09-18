import os
from dotenv import load_dotenv

load_dotenv()

PAT_TOKEN = os.getenv("PAT_TOKEN")
APP_ID = os.getenv("APP_ID")
BASE_URL = "https://api.derivws.com/trading/v1/options"

# Налаштування для Railway PostgreSQL та Telegram
DATABASE_URL = os.getenv("DATABASE_URL")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")