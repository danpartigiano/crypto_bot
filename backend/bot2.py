import redis
import logging
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def bot_worker(bot_id: str, redis_host: str = "localhost", redis_port: int = 6379):
    """
    Worker process for a bot that generates signals and pushes to Redis.

    Args:
        bot_id (str): Unique identifier for the bot.
        redis_host (str): Redis server host.
        redis_port (int): Redis server port.
    """
    redis_client = redis.StrictRedis(host=redis_host, port=redis_port, decode_responses=True)
    queue_name = f"{bot_id}_queue"

    logger.info(f"Bot {bot_id} started, pushing signals to {queue_name}")
    while True:
        try:
            # Generate a signal (e.g., "BUY:BTC" or "SELL:ETH")
            signal = generate_signal(bot_id)
            redis_client.rpush(queue_name, signal)
            logger.info(f"Bot {bot_id} pushed signal: {signal}")
            time.sleep(5)  # Adjust frequency as needed
        except Exception as e:
            logger.error(f"Error in bot {bot_id}: {e}")

def generate_signal(bot_id):
    """Dummy function to generate signals; replace with bot logic."""
    # import random
    # action = random.choice(["BUY", "SELL"])
    action = count
    count += 1
    crypto = "ETH"
    return f"{action}:{crypto}:{bot_id}"


if __name__ == "__main__":
    bot_worker("bot2")