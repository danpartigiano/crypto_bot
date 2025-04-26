# app/bots/CopyCatBot/signalGenerator.py

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


"""
CopyCatBot generator:
  - Tracks a specific Bitcoin whale address.
  - Fetches new on-chain transactions.
  - Emits BUY/SELL signals into Redis as JSON.
"""

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(f"CopyCatBot-generator")

# Configuration from environment
REDIS_HOST  = environment.REDIS_HOST
REDIS_PORT  = environment.REDIS_PORT
TARGET_ADDR = os.getenv("TARGET_BITCOIN_ADDRESS",
                        "bc1q5mecc0lj3mehs6jrv0j830fyxdtqhpx9d9durh")
API_BASE    = os.getenv("BLOCKCYPHER_API_URL",
                        "https://api.blockcypher.com")

MIN_INTERVAL     = 60  # seconds
_last_api_call   = 0
_transaction_cache = set()


def main(bot_id: int):
    queue = f"bot{bot_id}_queue"
    r     = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    r.delete(queue)

    logger.info(f"[Generator:{bot_id}] Tracking {TARGET_ADDR} → queue={queue}")

    while True:
        try:
            signals = _fetch_new_signals(bot_id, r)
            for s in signals:
                r.rpush(queue, s)
                logger.info(f"[Generator:{bot_id}] Pushed signal {s}")
            time.sleep(max(30, MIN_INTERVAL - (time.time() - _last_api_call)))
        except Exception as e:
            logger.error(f"[Generator:{bot_id}] Error: {e}")
            time.sleep(30)


def _fetch_new_signals(bot_id: int, r: redis.StrictRedis):
    global _last_api_call
    now = time.time()
    if now - _last_api_call < MIN_INTERVAL:
        return []
    _last_api_call = now

    # Load or initialize tracking info
    key = f"copycat:{bot_id}:target_trader"
    raw = r.get(key)
    info = json.loads(raw) if raw else {"btc_address": TARGET_ADDR, "last_check": now}

    url = f"{API_BASE}/v1/btc/main/addrs/{info['btc_address']}/full"
    resp = requests.get(url)
    signals = []

    if resp.status_code == 200:
        for tx in resp.json().get("txs", []):
            h = tx.get("hash")
            if h in _transaction_cache:
                continue
            _transaction_cache.add(h)

            ts_str = tx.get("received", "")[:19]
            ts = time.mktime(time.strptime(ts_str, "%Y-%m-%dT%H:%M:%S"))
            if ts <= info["last_check"]:
                continue

            incoming = any(info["btc_address"] in o.get("addresses", []) for o in tx.get("outputs", []))
            outgoing = any(info["btc_address"] in i.get("addresses", []) for i in tx.get("inputs", []))
            if incoming == outgoing:
                continue

            action = "BUY" if incoming else "SELL"
            sig = json.dumps({"id": int(time.time()), "action": action, "crypto": "BTC"})
            signals.append(sig)

    info["last_check"] = now
    r.set(key, json.dumps(info))
    return signals
