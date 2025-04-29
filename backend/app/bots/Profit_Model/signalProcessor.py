import os
import json
import time
import logging
import redis
from dotenv import load_dotenv, find_dotenv
from sqlalchemy.future import select

from app.utility.environment import environment
from app.utility.TokenService     import TokenService
from app.database.db_connection   import context_get_session
from app.database.models          import Subscription

# Locate and load .env
dotenv_path = find_dotenv()
if not dotenv_path:
    raise RuntimeError("Could not locate .env file")
load_dotenv(dotenv_path)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ProfitModel-processor")

# Redis config
REDIS_HOST = environment.REDIS_HOST
REDIS_PORT = environment.REDIS_PORT

class CoinbaseClient:
    def __init__(self, access_token: str):
        self.token = access_token

    def market_buy(self, product_id: str, quote_size: float) -> dict:
        import http.client, uuid
        conn = http.client.HTTPSConnection("api.coinbase.com")
        payload = {
            "client_order_id": str(uuid.uuid4()),
            "product_id":      product_id,
            "side":            "BUY",
            "order_configuration": {"market_market_ioc": {"quote_size": f"{quote_size:.2f}"}}
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        conn.request("POST", "/api/v3/brokerage/orders", json.dumps(payload), headers)
        resp = conn.getresponse()
        return json.loads(resp.read())

    def limit_sell(self, product_id: str, base_size: float, limit_price: float) -> dict:
        import http.client, uuid
        conn = http.client.HTTPSConnection("api.coinbase.com")
        payload = {
            "client_order_id": str(uuid.uuid4()),
            "product_id":      product_id,
            "side":            "SELL",
            "order_configuration": {
                "limit_limit_gtc": {
                    "base_size":   f"{base_size:.4f}",
                    "limit_price": f"{limit_price:.4f}"
                }
            }
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        conn.request("POST", "/api/v3/brokerage/orders", json.dumps(payload), headers)
        resp = conn.getresponse()
        return json.loads(resp.read())

def main(bot_id: int):
    r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    queue = f"bot{bot_id}_queue"
    logger.info(f"[Proc:{bot_id}] Listening on {queue}")

    while True:
        try:
            item = r.blpop(queue, timeout=10)
            if not item:
                continue

            _, raw = item
            sig = json.loads(raw)
            logger.info(f"[Proc:{bot_id}] Got signal {sig}")

            _execute_for_all(bot_id, sig)

        except Exception as e:
            logger.error(f"[Proc] Loop error: {e}")
            time.sleep(5)


def _execute_for_all(bot_id: int, sig: dict):
    with context_get_session() as db:
        subs = db.scalars(
            select(Subscription).where(Subscription.bot_id == bot_id)
        ).all()

        for sub in subs:
            try:
                # Fetch user token
                token_svc = TokenService(user_id=sub.user_id, db=db)
                user_tok  = token_svc.get_access_token(exchange_name="coinbase")
                client    = CoinbaseClient(user_tok)

                # Execute the appropriate order
                if sig["action"] == "BUY":
                    resp = client.market_buy(sig["product_id"], sig["quote_size"])
                else:
                    resp = client.limit_sell(
                        sig["product_id"],
                        sig.get("quote_size", 0.0),
                        sig["limit_price"]
                    )
                logger.info(f"[Proc] Executed {sig['action']} for user {sub.user_id}: {resp}")

            except Exception as e:
                logger.error(f"[Proc] Failed {sig['action']} for user {sub.user_id}: {e}")
