from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, db_manager, account_manager):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.chat_id = chat_id
        self.db = db_manager
        self.acc = account_manager
        self._register_handlers()

    def _register_handlers(self):
        @self.dp.message(Command("stats"))
        async def send_stats(message: types.Message):
            # Захист: відповідаємо лише власнику
            if str(message.chat.id) != str(self.chat_id):
                return
            
            # Отримуємо дані з БД
            stats = await self.db.get_statistics()
            total = stats["total"]
            wins = stats["wins"]
            winrate = (wins / total * 100) if total > 0 else 0.0
            
            # Оновлюємо баланс через AccountManager
            self.acc.connect()
            
            text = (
                f"📊 <b>Статистика Торгового Бота</b>\n\n"
                f"💰 <b>Баланс:</b> {self.acc.balance} {self.acc.currency}\n"
                f"🎯 <b>Win Rate:</b> {winrate:.1f}%\n"
                f"📈 <b>Всього угод у БД:</b> {total}"
            )
            await message.answer(text, parse_mode="HTML")

    async def send_notification(self, text: str):
        """Відправляє повідомлення у визначений чат."""
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode="HTML")
        except Exception as e:
            print(f"❌ [Telegram] Помилка відправки: {e}")

    async def start_polling(self):
        """Запускає слухача команд (працює у фоні)."""
        print("🤖 [Telegram] Бот готовий приймати команди.")
        await self.dp.start_polling(self.bot)