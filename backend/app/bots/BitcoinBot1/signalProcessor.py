from app.utility.environment import environment
from app.utility.TokenService import TokenService
from app.database.db_connection import context_get_session
from app.database.models import Subscription
import redis
import logging
from sqlalchemy.future import select
import os
import sys, getopt
from app.utility.environment import environment


# Logging per bot
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(os.path.basename(os.getcwd()))


def execute_trades(bot_id: int):

    redis_client = redis.StrictRedis(host=environment.REDIS_HOST, port=environment.REDIS_PORT, decode_responses=True)

    queue_name = f"bot{bot_id}_queue"

    logger.info(f"Trade executor for bot {bot_id} started, reading signals from {queue_name}")

    while True:

        try:

            signal = redis_client.blpop(queue_name, timeout=10)

            if signal:
                _, trade_signal = signal  # Extract trade signal

                logger.info(f"Signal {trade_signal} currently being processed")

                process_trade_for_all(trade_signal, bot_id)

            else:
                logger.info(f"No signals in {queue_name}, waiting...")

        except Exception as e:

            logger.error(f"Error in execute_trades for bot {bot_id}: {e}")


    

    pass

def process_trade_for_all(signal: str, bot_id: int):

    #get all users subscribed for this bot
    with context_get_session() as db:

        subscriptions = db.scalars(select(Subscription).where(Subscription.bot_id == bot_id)).all()

        for subscription in subscriptions:

            try:
                #get this users access key
                token_service = TokenService(user_id=subscription.user_id, db=db)

                access_token = token_service.get_access_token(exchange_name="coinbase")

                #add logic to make coinbase trade via coinbase library client
                logger.info(f"Executing trade {signal} for user {subscription.user_id}")

            except Exception as e:
                logger.error(f"Unable to process {signal} for user {subscription.user_id}")



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
    logger.name = f"bot {bot_id} executor"

    execute_trades(bot_id)

    


if __name__ == "__main__":
    main(get_bot_id(sys.argv[1:]))