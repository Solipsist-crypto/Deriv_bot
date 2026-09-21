import asyncpg
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        """Створює пул з'єднань та ініціалізує таблицю."""
        self.pool = await asyncpg.create_pool(self.db_url)
        await self._init_db()

    async def _init_db(self):
        query = """
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            symbol VARCHAR(20),
            close_price FLOAT,
            rsi FLOAT,
            rsi_signal VARCHAR(10),
            ema_signal VARCHAR(10),
            bb_signal VARCHAR(10),
            buy_votes INT,
            sell_votes INT,
            signal VARCHAR(10),
            contract_id VARCHAR(50),
            stake FLOAT,
            profit FLOAT,
            win INT
        );
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)
            print("📁 [Database] Таблицю trades підготовлено (PostgreSQL).")

    async def log_trade(self, analysis: dict, trade: dict, stake: float):
        """Записує угоду в базу даних."""
        if not trade:
            return

        query = """
        INSERT INTO trades (
            timestamp, symbol, close_price, rsi, rsi_signal, ema_signal, bb_signal, 
            buy_votes, sell_votes, signal, contract_id, stake, profit, win
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                datetime.now(),
                analysis.get("symbol", ""),
                float(analysis.get("close_price", 0.0)),
                float(analysis.get("rsi", 0.0) or 0.0),
                analysis.get("rsi_signal", ""),
                analysis.get("ema_signal", ""),
                analysis.get("bb_signal", ""),
                int(analysis.get("buy_votes", 0)),
                int(analysis.get("sell_votes", 0)),
                analysis.get("signal", ""),  # Беремо сигнал з індикаторного аналізу
                str(trade.get("contract_id", "")),
                float(stake),
                float(trade.get("profit", 0.0)),
                int(trade.get("win", 0))
            )
            print(f"💾 [Database] Угоду {trade.get('contract_id')} збережено в БД.")

    async def get_statistics(self) -> dict:
        """Повертає статистику для Telegram-бота."""
        query_total = "SELECT COUNT(*) FROM trades;"
        query_wins = "SELECT COUNT(*) FROM trades WHERE win = 1;"
        
        async with self.pool.acquire() as conn:
            total = await conn.fetchval(query_total)
            wins = await conn.fetchval(query_wins)
            
        return {"total": total or 0, "wins": wins or 0}