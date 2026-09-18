import asyncio
from account import AccountManager
from market import MarketManager
from strategy import MultiIndicatorStrategy
from trader import TraderManager
from database import DatabaseManager
from tg_bot import TelegramNotifier
from config import DATABASE_URL, TG_BOT_TOKEN, TG_CHAT_ID

SYMBOLS = ["frxXAUUSD", "frxEURUSD", "frxGBPUSD", "frxUSDJPY", "frxAUDUSD"]
STAKE_AMOUNT = 5.0
EXPIRATION_MINUTES = 15
TIMEFRAME_SECONDS = 900
INTERVAL_SECONDS = 300

background_tasks = set()

async def handle_trade_task(trader, db, tg, acc, symbol, signal, analysis):
    """Фонова задача: відкриває угоду, чекає результат, пише в БД та надсилає пуш."""
    
    # 1. Повідомляємо про старт
    await tg.send_notification(f"🚀 <b>Вхід у ринок:</b> {symbol}\n🔔 <b>Сигнал:</b> {signal}\n💵 <b>Ціна:</b> {analysis['close_price']}")
    
    trade_result = await trader.execute_trade(
        symbol=symbol, signal=signal, amount=STAKE_AMOUNT, 
        duration=EXPIRATION_MINUTES, duration_unit="m"
    )
    
    if trade_result:
        analysis['symbol'] = symbol
        
        # 2. Записуємо в PostgreSQL
        await db.log_trade(analysis_data=analysis, trade_result=trade_result, stake=STAKE_AMOUNT)
        
        # 3. Повідомляємо про результат
        status_icon = "🟢" if trade_result["win"] else "🔴"
        profit_str = f"{trade_result['profit']:+.2f}"
        
        await tg.send_notification(
            f"{status_icon} <b>Угоду закрито:</b> {symbol}\n"
            f"📊 <b>Результат:</b> {trade_result['status'].upper()}\n"
            f"💵 <b>Профіт:</b> {profit_str} USD"
        )

async def scan_and_trade(acc, market, strategy, trader, db, tg):
    print("\n--------------------------------------------------")
    print("📊 Початок нового циклу сканування (асинхронний режим)...")
    
    for symbol in SYMBOLS:
        print(f"\n--- Аналіз {symbol} ---")
        candles = await market.get_candles(symbol=symbol, count=100, timeframe=TIMEFRAME_SECONDS)

        if candles:
            analysis = strategy.analyze(candles)
            signal = analysis['signal']
            print(f"💵 Ціна: {analysis['close_price']} | Сигнал: {signal}")

            if signal in ["BUY", "SELL"]:
                task = asyncio.create_task(
                    handle_trade_task(trader, db, tg, acc, symbol, signal, analysis)
                )
                background_tasks.add(task)
                task.add_done_callback(background_tasks.discard)
        else:
            print(f"❌ Не вдалося отримати свічки для {symbol}")

        await asyncio.sleep(1)

async def main():
    print("🚀 Запуск ML Торгового Бота (PostgreSQL + Telegram)...")
    
    acc = AccountManager()
    if not acc.connect():
        print("🛑 Помилка авторизації в AccountManager.")
        return

    # Ініціалізація бази даних та підключення
    db = DatabaseManager(db_url=DATABASE_URL)
    await db.connect()

    market = MarketManager(acc)
    strategy = MultiIndicatorStrategy()
    trader = TraderManager(acc)
    
    # Ініціалізація Telegram Бота
    tg = TelegramNotifier(token=TG_BOT_TOKEN, chat_id=TG_CHAT_ID, db_manager=db, account_manager=acc)
    
    # Запускаємо фонове слухання команд Telegram (наприклад, /stats)
    asyncio.create_task(tg.start_polling())
    
    await tg.send_notification("✅ Торговий бот успішно запущений та моніторить ринок.")

    try:
        while True:
            await scan_and_trade(acc, market, strategy, trader, db, tg)
            print(f"\n⏳ Наступна перевірка через {INTERVAL_SECONDS // 60} хв...")
            await asyncio.sleep(INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        print("\n🛑 Бота зупинено вручну (Ctrl+C).")
        await tg.send_notification("🛑 Бота зупинено.")

if __name__ == "__main__":
    asyncio.run(main())