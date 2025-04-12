import redis
from app.bots.celery.celery_app import execute_trade  # Celery task

def process_queue_with_lock(queue_name, redis_client):
    lock_key = f"queue_lock:{queue_name}"
    lock_ttl = 10  # Lock expiration time in seconds

    # Attempt to acquire the lock
    if redis_client.set(lock_key, "locked", ex=lock_ttl, nx=True):  # nx=True ensures no overwriting
        try:
            signal = redis_client.lpop(queue_name)
            if signal:
                # Dispatch the task asynchronously to Celery workers
                execute_trade.delay(signal)  # Non-blocking!
        finally:
            # Release the lock by deleting it
            redis_client.delete(lock_key)
    else:
        # Another worker has the lock
        print(f"Queue {queue_name} is locked by another worker. Skipping...")

def trade_consumer(redis_host="localhost", redis_port=6379):
    redis_client = redis.StrictRedis(host=redis_host, port=6379, decode_responses=True)
    while True:
        bot_queues = redis_client.keys("bot_*_queue")
        for queue_name in bot_queues:
            process_queue_with_lock(queue_name, redis_client)