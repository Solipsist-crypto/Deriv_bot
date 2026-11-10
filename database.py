import asyncpg
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.db_url)
        await self._init_db()

    async def _init_db(self):
        create_query = """
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP, symbol VARCHAR(20), close_price FLOAT,
            rsi FLOAT, rsi_signal VARCHAR(10), ema_signal VARCHAR(10), bb_signal VARCHAR(10),
            macd FLOAT, macd_signal VARCHAR(10), atr FLOAT,
            hour INT, dayofweek INT, buy_votes INT, sell_votes INT, signal VARCHAR(10),
            contract_id VARCHAR(50), stake FLOAT, profit FLOAT, win INT,
            ema_fast FLOAT, ema_slow FLOAT, ema_distance_pct FLOAT,
            macd_line FLOAT, macd_signal_line FLOAT, macd_hist FLOAT,
            bb_upper FLOAT, bb_lower FLOAT, bb_width FLOAT, bb_position FLOAT,
            rsi_slope FLOAT, atr_percentile FLOAT, adx FLOAT
        );
        """
        async with self.pool.acquire() as conn:
            await conn.execute(create_query)
            print("📁 [Database] Таблицю trades створено/перевірено (PostgreSQL) з усіма ML-фічами.")

    async def log_trade(self, analysis: dict, trade: dict, stake: float):
        if not trade: return
        now = datetime.now()
        query = """
        INSERT INTO trades (
            timestamp, symbol, close_price, rsi, rsi_signal, ema_signal, bb_signal, 
            macd, macd_signal, atr, hour, dayofweek, buy_votes, sell_votes, signal, contract_id, stake, profit, win,
            ema_fast, ema_slow, ema_distance_pct, macd_line, macd_signal_line, macd_hist, 
            bb_upper, bb_lower, bb_width, bb_position, rsi_slope, atr_percentile, adx
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19,
            $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32
        )
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                now, analysis.get("symbol", ""), float(analysis.get("close_price", 0.0)),
                float(analysis.get("rsi", 50.0) or 50.0), analysis.get("rsi_signal", ""),
                analysis.get("ema_signal", ""), analysis.get("bb_signal", ""),
                float(analysis.get("macd_line", 0.0)), analysis.get("macd_signal", ""), 
                float(analysis.get("atr", 0.0)), now.hour, now.weekday(),
                int(analysis.get("buy_votes", 0)), int(analysis.get("sell_votes", 0)),
                analysis.get("signal", ""), str(trade.get("contract_id", "")),
                float(stake), float(trade.get("profit", 0.0)), int(trade.get("win", 0)),
                float(analysis.get("ema_fast", 0.0) or 0.0), float(analysis.get("ema_slow", 0.0) or 0.0),
                float(analysis.get("ema_distance_pct", 0.0) or 0.0), float(analysis.get("macd_line", 0.0) or 0.0),
                float(analysis.get("macd_signal_line", 0.0) or 0.0), float(analysis.get("macd_hist", 0.0) or 0.0),
                float(analysis.get("bb_upper", 0.0) or 0.0), float(analysis.get("bb_lower", 0.0) or 0.0),
                float(analysis.get("bb_width", 0.0) or 0.0), float(analysis.get("bb_position", 0.5) or 0.5),
                float(analysis.get("rsi_slope", 0.0) or 0.0), float(analysis.get("atr_percentile", 0.5) or 0.5),
                float(analysis.get("adx", 0.0) or 0.0)
            )
            print(f"💾 [Database] Угоду {trade.get('contract_id')} збережено з усіма ML-фічами.")

    async def get_statistics(self) -> dict:
        query_total = "SELECT COUNT(*) FROM trades;"
        query_wins = "SELECT COUNT(*) FROM trades WHERE win = 1;"
        async with self.pool.acquire() as conn:
            total = await conn.fetchval(query_total)
            wins = await conn.fetchval(query_wins)
        return {"total": total or 0, "wins": wins or 0}