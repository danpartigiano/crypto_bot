import redis
import logging
import time
import os
import sys, getopt
from app.utility.environment import environment


"""Example bot that sends trading signals to a redis queue to be processed by the signalProcessor
    This seperation of signal generating and processing decouples the automated trading
    so that neither process can bogg down the other. Also the python GIL kinda prevents us
    from placing the logic of both in one file."""


# Logging per bot
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(os.path.basename(os.getcwd()))

count = 0

def bot_worker(bot_id: int):
    """Main worker function that waits for a signal then pushes it to the bot's redis signal queue"""

    redis_client = redis.StrictRedis(host=environment.REDIS_HOST, port=environment.REDIS_PORT, decode_responses=True)
    
    queue_name = f"bot{bot_id}_queue"

    #remove any stale trades still on the queue - optional
    redis_client.delete(queue_name)

    logger.info(f"Bot {bot_id} started, pushing signals to {queue_name}")

    while True:

        try:

            signal = generate_signal()
            redis_client.rpush(queue_name, signal)
            logger.info(f"Bot {bot_id} pushed signal: {signal}")
            time.sleep(2)

        except Exception as e:
            logger.error(f"Error in bot {bot_id}: {e}")

def generate_signal():
    """Dummy function to generate signals, place signal generating logic here"""

    import random
    action = random.choice(["BUY", "SELL"])
    global count
    count += 1
    crypto = "ETH"
    return f"{count}:{action}:{crypto}"

def get_bot_id(argv):
    # get bot id from command line
    try:
       opts, _ = getopt.getopt(argv,"id:")
       if opts and opts[0][0] == "-id":
           return opts[0][1]
       
       logger.error("No bot id found")
       sys.exit(2)
    except getopt.GetoptError:
       logger.error("Unable to get bot id")
       sys.exit(2)

def main(bot_id: int):
    logger.name = f"bot {bot_id} generator"

    bot_worker(bot_id)
    


if __name__ == "__main__":
    main(get_bot_id(sys.argv[1:]))

