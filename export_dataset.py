import asyncio
import pandas as pd
import asyncpg

# Публічний URL для підключення з ПК
PUBLIC_DATABASE_URL = "postgresql://postgres:tzRYOayVRDHBsCQUZbdrngLfytCnDEwn@nozomi.proxy.rlwy.net:27027/railway"

async def main():
    print("📥 Підключаємося до бази даних PostgreSQL на Railway через Public Proxy...")
    
    try:
        conn = await asyncpg.connect(PUBLIC_DATABASE_URL)
    except Exception as e:
        print(f"❌ Помилка підключення: {e}")
        return

    print("📊 Отримуємо всі угоди з таблиці trades...")
    rows = await conn.fetch("SELECT * FROM trades ORDER BY id ASC;")
    await conn.close()

    if not rows:
        print("⚠️ Таблиця trades порожня або не знайдена.")
        return

    # Конвертуємо SQL-записи в Pandas DataFrame
    data = [dict(r) for r in rows]
    df = pd.DataFrame(data)

    # Зберігаємо у CSV
    output_filename = "trades_dataset.csv"
    df.to_csv(output_filename, index=False, encoding="utf-8")

    print(f"\n✅ Успішно збережено {len(df)} угод у файл: {output_filename}")
    print("\n🔍 Перші 5 рядків датасету:")
    print(df[["symbol", "close_price", "rsi", "buy_votes", "sell_votes", "signal", "profit", "win"]].head())

if __name__ == "__main__":
    asyncio.run(main())