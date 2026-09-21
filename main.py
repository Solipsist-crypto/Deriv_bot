import asyncio
import websockets
from datetime import datetime, timezone
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
active_trades = set()

async def handle_trade_task(trader, db, tg, acc, symbol, signal, analysis):
    """Фонова задача: відкриває угоду, чекає результат, пише в БД та надсилає пуш."""
    try:
        active_trades.add(symbol)
        await tg.send_notification(f"🚀 <b>Вхід у ринок:</b> {symbol}\n🔔 <b>Сигнал:</b> {signal}\n💵 <b>Ціна:</b> {analysis['close_price']}")
        
        trade_result = await trader.execute_trade(
            symbol=symbol, signal=signal, amount=STAKE_AMOUNT, 
            duration=EXPIRATION_MINUTES, duration_unit="m"
        )
        
        if trade_result:
            analysis['symbol'] = symbol
            await db.log_trade(analysis_data=analysis, trade_result=trade_result, stake=STAKE_AMOUNT)
            
            status_icon = "🟢" if trade_result["win"] else "🔴"
            profit_str = f"{trade_result['profit']:+.2f}"
            
            await tg.send_notification(
                f"{status_icon} <b>Угоду закрито:</b> {symbol}\n"
                f"📊 <b>Результат:</b> {trade_result['status'].upper()}\n"
                f"💵 <b>Профіт:</b> {profit_str} USD"
            )
    except Exception as e:
        print(f"❌ Помилка у фоновій задачі угоди для {symbol}: {e}")
        await tg.send_notification(f"⚠️ <b>Помилка угоди ({symbol}):</b> {e}")
    finally:
        active_trades.discard(symbol)

async def scan_and_trade(acc, market, strategy, trader, db, tg):
    print("\n--------------------------------------------------")
    print("📊 Початок нового циклу сканування (асинхронний режим)...")
    
    # Отримуємо URL і відкриваємо ОДНЕ з'єднання для всього циклу
    ws_url = await acc.get_otp_url()
    if not ws_url:
        print("❌ Не вдалося отримати WebSocket URL для сканування.")
        return

    try:
        async with websockets.connect(ws_url, open_timeout=15) as ws:
            for symbol in SYMBOLS:
                if symbol in active_trades:
                    print(f"⏳ Угода по {symbol} ще відкрита. Пропускаємо сканування.")
                    continue

                print(f"\n--- Аналіз {symbol} ---")
                try:
                    # Передаємо відкритий сокет ws у функцію
                    candles = await market.get_candles(ws, symbol=symbol, count=100, timeframe=TIMEFRAME_SECONDS)

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
                except Exception as e:
                    print(f"❌ Помилка аналізу {symbol}: {e}")

                await asyncio.sleep(1) # Секундна пауза між запитами, як у тестовому скрипті
    except Exception as e:
        print(f"❌ Помилка з'єднання WebSocket у циклі: {e}")

async def main():
    print("🚀 Запуск ML Торгового Бота (PostgreSQL + Telegram)...")
    
    acc = AccountManager()
    is_connected = await acc.connect()
    if not is_connected:
        print("🛑 Помилка авторизації в AccountManager.")
        return

    db = DatabaseManager(db_url=DATABASE_URL)
    await db.connect()

    market = MarketManager(acc)
    strategy = MultiIndicatorStrategy()
    trader = TraderManager(acc)
    
    tg = TelegramNotifier(token=TG_BOT_TOKEN, chat_id=TG_CHAT_ID, db_manager=db, account_manager=acc)
    asyncio.create_task(tg.start_polling())
    
    await tg.send_notification("✅ Торговий бот успішно запущений та моніторить ринок.")

    try:
        while True:
            try:
                now = datetime.now(timezone.utc)
                hour = now.hour
                weekday = now.weekday()

                is_weekend = (weekday == 5) or (weekday == 4 and hour >= 23) or (weekday == 6 and hour < 21)
                is_night = (hour >= 21 or hour < 2) and not (weekday == 6 and hour >= 21) and not (weekday == 0 and hour < 2)

                if is_weekend or is_night:
                    reason = "Вихідні на біржі" if is_weekend else "Нічна перерва"
                    print(f"😴 {reason} (Поточний час: {hour:02d}:{now.minute:02d} UTC). Бот відпочиває...")
                    await asyncio.sleep(INTERVAL_SECONDS)
                    continue

                await scan_and_trade(acc, market, strategy, trader, db, tg)
                print(f"\n⏳ Наступна перевірка через {INTERVAL_SECONDS // 60} хв...")
                await asyncio.sleep(INTERVAL_SECONDS)
            
            except Exception as loop_error:
                print(f"❌ Збій у головному циклі: {loop_error}")
                print("🔄 Спроба перепідключення до акаунту...")
                await acc.connect()
                await asyncio.sleep(10)

    except KeyboardInterrupt:
        print("\n🛑 Бота зупинено вручну (Ctrl+C).")
        await tg.send_notification("🛑 Бота зупинено.")

if __name__ == "__main__":
    asyncio.run(main())