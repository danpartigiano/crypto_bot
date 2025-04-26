# app/bots/CopyCatBot/signalProcessor.py

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

# Locate and load the project’s .env
dotenv_path = find_dotenv()
if not dotenv_path:
    raise RuntimeError("Could not locate .env file")
load_dotenv(dotenv_path)


"""
CopyCatBot processor:
  - BLPOP’s JSON signals from Redis.
  - Runs risk checks.
  - Executes BUY/SELL on Coinbase for each subscriber using their token.
"""

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(f"CopyCatBot-processor")

# Configuration from environment
REDIS_HOST = environment.REDIS_HOST
REDIS_PORT = environment.REDIS_PORT


def main(bot_id: int):
    r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    queue = f"bot{bot_id}_queue"
    logger.info(f"[Processor:{bot_id}] Listening on {queue}")

    while True:
        try:
            item = r.blpop(queue, timeout=10)
            if not item:
                continue

            _, raw = item
            sig = json.loads(raw)
            logger.info(f"[Processor:{bot_id}] Got signal {sig}")

            if not _risk_ok(r, bot_id, sig):
                logger.warning(f"[Processor:{bot_id}] Signal rejected by risk mgmt")
                continue

            _execute_for_subscribers(bot_id, sig)

        except Exception as e:
            logger.error(f"[Processor:{bot_id}] Loop error: {e}")
            time.sleep(5)


def _risk_ok(r: redis.StrictRedis, bot_id: int, sig: dict) -> bool:
    # Insert your existing trade-frequency / time-of-day / balance checks here.
    return True


def _execute_for_subscribers(bot_id: int, sig: dict):
    with context_get_session() as db:
        subs = db.scalars(
            select(Subscription).where(Subscription.bot_id == bot_id)
        ).all()

        for sub in subs:
            try:
                ts        = TokenService(user_id=sub.user_id, db=db)
                user_tok  = ts.get_access_token(exchange_name="coinbase")
                # Here you’d instantiate your Coinbase REST client with user_tok
                logger.info(f"[Processor:{bot_id}] Executing {sig['action']} for user {sub.user_id}")
            except Exception as e:
                logger.error(f"[Processor:{bot_id}] Fail for user {sub.user_id}: {e}")
