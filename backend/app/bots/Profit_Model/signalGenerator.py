import os
import time
import json
import logging
import redis
import requests
from dotenv import load_dotenv, find_dotenv
from app.utility.environment import environment

# Locate and load the project’s .env
dotenv_path = find_dotenv()
if not dotenv_path:
    raise RuntimeError("Could not locate .env file")
load_dotenv(dotenv_path)

# Configuration
DEFAULT_PROFIT_TARGET   = 0.25    # 25% profit if not overridden
MIN_PRICE_CHANGE_24_HRS = 0.10    # 10% 24h gain threshold
BASE_URL                = "api.coinbase.com"

class CoinbaseClient:
    def __init__(self, access_token: str):
        self.token = access_token

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        import http.client
        conn = http.client.HTTPSConnection(BASE_URL)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        body = json.dumps(payload) if payload else None
        conn.request(method, path, body, headers)
        resp = conn.getresponse()
        data = resp.read()
        if resp.status >= 400:
            raise RuntimeError(f"{resp.status} on {path}: {data.decode()}")
        return json.loads(data)

    def get_products(self) -> list[dict]:
        return self._request("GET", "/api/v3/brokerage/products").get("products", [])

    def list_open_sell_orders(self) -> set[str]:
        orders = self._request("GET", "/api/v3/brokerage/orders?side=SELL&status=OPEN")
        return {o["product_id"] for o in orders.get("orders", [])}

def main(bot_id: int):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(f"ProfitModel-generator-{bot_id}")

    # Redis client from centralized environment
    r = redis.StrictRedis(
        host=environment.REDIS_HOST,
        port=environment.REDIS_PORT,
        decode_responses=True
    )
    queue = f"bot{bot_id}_queue"
    r.delete(queue)

    logger.info(f"[Gen:{bot_id}] Starting up, pushing to {queue}")

    # Load profit target override if present
    profit_target = float(os.getenv("TARGET_PROFIT", DEFAULT_PROFIT_TARGET))

    client = CoinbaseClient(os.getenv("ACCESS_TOKEN"))

    while True:
        try:
            # 1) Exclude any assets already on open SELL orders
            selling = client.list_open_sell_orders()

            # 2) Fetch all spot products and filter candidates
            candidates = [
                p for p in client.get_products()
                if p["product_id"].endswith("USD")
                   and float(p["price_percentage_change_24h"]) > MIN_PRICE_CHANGE_24_HRS
                   and p["product_id"] not in selling
            ]
            if not candidates:
                logger.info("[Gen] No buy candidates—sleeping")
                time.sleep(10)
                continue

            # 3) Determine per-asset allocation
            #    (for brevity, assume a fixed $100 per trade)
            allocation = 100.0

            # 4) Push a BUY signal + limit SELL signal for each candidate
            for p in candidates:
                pid   = p["product_id"]
                price = float(p["price"])
                signal = {
                    "action":      "BUY",
                    "product_id":  pid,
                    "quote_size":  round(allocation, 2),
                    "limit_price": round(price * (1 + profit_target), 4)
                }
                r.rpush(queue, json.dumps(signal))
                logger.info(f"[Gen] Pushed signal {signal}")

            time.sleep(5)

        except Exception as e:
            logger.error(f"[Gen] Error: {e}")
            time.sleep(10)
