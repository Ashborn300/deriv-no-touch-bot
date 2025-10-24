# bot_notouch.py
import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from deriv_api import DerivAPI
import pandas as pd
import numpy as np
import csv

load_dotenv()

APP_ID = int(os.getenv("DERIV_APP_ID", "1"))
API_TOKEN = os.getenv("DERIV_API_TOKEN")
SYMBOL = os.getenv("SYMBOL", "1HZ10V")
DURATION_MINUTES = int(os.getenv("DURATION_MINUTES", "2"))
BARRIER_DISTANCE = float(os.getenv("BARRIER_DISTANCE", "1.55"))
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "10"))
CURRENCY = os.getenv("CURRENCY", "USD")
MAX_OPEN = int(os.getenv("MAX_OPEN", "1"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DerivBot")

# =========================
# Utils & indicateurs
# =========================

def ema(series, period=100):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def is_hammer(o, c, h, l):
    body = abs(c - o)
    lower_wick = o - l if c > o else c - l
    upper_wick = h - c if c > o else h - o
    return lower_wick > 2 * body and upper_wick < body

def is_inverted_hammer(o, c, h, l):
    body = abs(c - o)
    upper_wick = h - c if c > o else h - o
    lower_wick = o - l if c > o else c - l
    return upper_wick > 2 * body and lower_wick < body

def detect_levels(df, window=10, tolerance=0.001):
    supports, resistances = [], []
    for i in range(window, len(df) - window):
        local_low = df["Low"][i]
        local_high = df["High"][i]
        if local_low == min(df["Low"][i-window:i+window]):
            if not any(abs(local_low - s) < tolerance for s in supports):
                supports.append(local_low)
        if local_high == max(df["High"][i-window:i+window]):
            if not any(abs(local_high - r) < tolerance for r in resistances):
                resistances.append(local_high)
    return supports, resistances

def near_level(price, levels, threshold=0.001):
    return any(abs(price - level) / price < threshold for level in levels)

def log_trade(data, filename="trades_log.csv"):
    file_exists = os.path.isfile(filename)
    with open(filename, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

# =========================
# Bot principal
# =========================

class NoTouchBot:
    def __init__(self):
        self.api = DerivAPI(app_id=APP_ID)
        self.df = pd.DataFrame(columns=["Open", "High", "Low", "Close"])
        self.open_positions = 0

        # Martingale cycle: 2 → 6 → 18 → 60 → reset
        self.stake_cycle = [2.0, 6.0, 18.0, 60.0]
        self.current_step = 0  # index dans stake_cycle

    async def health_check(self):
        try:
            res = await self.api.authorize(API_TOKEN)
            auth = res["authorize"]
            loginid = auth.get("loginid")
            is_virtual = auth.get("is_virtual")
            balance = auth.get("balance")
            currency = auth.get("currency")
            account_type = "💎 DÉMO" if is_virtual else "🔥 RÉEL"
            logger.info(f"Connexion OK — {loginid} ({account_type}) | Solde : {balance:.2f} {currency}")
            return True
        except Exception as e:
            logger.error(f"Échec du test de connexion : {e}")
            return False

    async def authorize(self):
        res = await self.api.authorize(API_TOKEN)
        acc = res["authorize"]
        logger.info(f"Autorisé sur {acc['loginid']} ({'Démo' if acc['is_virtual'] else 'Réel'})")

    def current_stake(self) -> float:
        return self.stake_cycle[self.current_step]

    def advance_after_result(self, profit: float):
        # gain → reset au début ; perte → étape suivante (et boucle)
        if profit > 0:
            self.current_step = 0
        else:
            self.current_step = (self.current_step + 1) % len(self.stake_cycle)

    async def tick_collector(self):
        await self.api.ticks({"ticks_history": SYMBOL, "end": "latest", "count": 1000})
        async for tick in self.api.subscribe_to_ticks(SYMBOL):
            yield tick

    async def analyze_and_trade(self, candles):
        df = pd.DataFrame(candles, columns=["Open","High","Low","Close"])
        df["EMA100"] = ema(df["Close"], 100)
        df["RSI"] = rsi(df["Close"])
        supports, resistances = detect_levels(df)
        o, h, l, c = df.iloc[-1][["Open","High","Low","Close"]]
        ema100, rsi_val = df["EMA100"].iloc[-1], df["RSI"].iloc[-1]

        # Barrière inversée
        if c > ema100 and is_hammer(o,c,h,l) and near_level(l,supports) and rsi_val < 45:
            barrier_sign = "-"
        elif c < ema100 and is_inverted_hammer(o,c,h,l) and near_level(h,resistances) and rsi_val > 55:
            barrier_sign = "+"
        else:
            barrier_sign = None

        if barrier_sign and self.open_positions < MAX_OPEN:
            await self.buy_notouch(barrier_sign)

    async def buy_notouch(self, sign):
        stake_amt = self.current_stake()
        barrier = f"{sign}{BARRIER_DISTANCE}"
        proposal_req = {
            "proposal": 1,
            "amount": stake_amt,
            "basis": "stake",
            "contract_type": "NOTOUCH",
            "currency": CURRENCY,
            "symbol": SYMBOL,
            "duration": DURATION_MINUTES,
            "duration_unit": "m",
            "barrier": barrier
        }
        prop = await self.api.proposal(proposal_req)
        price = float(prop["proposal"]["ask_price"])
        pid = prop["proposal"]["id"]
        buy = await self.api.buy({"buy": pid, "price": price})
        self.open_positions += 1
        cid = buy["buy"]["contract_id"]
        logger.info(f"🟢 Achat NOTOUCH {barrier} ({cid}) stake={stake_amt}$ durée={DURATION_MINUTES}m [step {self.current_step+1}/{len(self.stake_cycle)}]")

        log_trade({
            "time": datetime.utcnow().isoformat(),
            "event": "OPEN",
            "symbol": SYMBOL,
            "barrier": barrier,
            "stake": stake_amt,
            "duration": DURATION_MINUTES,
            "direction": "haussier" if sign == "-" else "baissier",
            "profit": None,
            "martingale_step": self.current_step+1
        })

    async def track_pnl(self):
        await self.api.proposal_open_contract({"proposal_open_contract": 1, "subscribe": 1})
        async for msg in self.api.subscribe():
            poc = msg.get("proposal_open_contract")
            if not poc:
                continue
            if poc.get("is_sold"):
                profit = float(poc.get("profit", 0))
                self.open_positions = max(0, self.open_positions - 1)
                logger.info(f"Contrat clôturé | P/L={profit:.2f}$ | Open={self.open_positions}")
                log_trade({
                    "time": datetime.utcnow().isoformat(),
                    "event": "CLOSE",
                    "symbol": SYMBOL,
                    "barrier": "unknown",
                    "stake": None,
                    "duration": DURATION_MINUTES,
                    "direction": "N/A",
                    "profit": profit,
                    "martingale_step": self.current_step+1
                })
                # avancer la martingale après le résultat
                self.advance_after_result(profit)

    async def run(self):
        ok = await self.health_check()
        if not ok:
            logger.error("❌ Vérifie ton TOKEN ou ton APP_ID avant de continuer.")
            return

        await self.authorize()
        asyncio.create_task(self.track_pnl())

        ticks = []
        async for tick in self.tick_collector():
            ticks.append(float(tick["tick"]["quote"]))
            if len(ticks) >= 5:  # regroupe 5 ticks → 1 bougie
                o, h, l, c = ticks[0], max(ticks), min(ticks), ticks[-1]
                self.df.loc[len(self.df)] = [o, h, l, c]
                if len(self.df) > 200:
                    self.df = self.df.iloc[-200:]
                await self.analyze_and_trade(self.df.tail(100))
                ticks = []
                await asyncio.sleep(COOLDOWN_SECONDS)

async def main():
    bot = NoTouchBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Arrêt manuel du bot.")
