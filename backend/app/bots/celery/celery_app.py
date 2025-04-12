from celery import Celery
import logging

logger = logging.getLogger("execution")

app = Celery(
    "trade_executor",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)


# Route tasks based on queue name
app.conf.task_routes = {
    "trade_tasks.bot1": {"queue": "bot1_queue"},
    "trade_tasks.bot2": {"queue": "bot2_queue"}
}

@app.task(name="trade_tasks.bot1")  # Corresponds to bot1_queue
def execute_trade_bot1(signal):
    print(f"Executing trade for bot1: {signal}")

@app.task(name="trade_tasks.bot2")  # Corresponds to bot2_queue
def execute_trade_bot2(signal):
    print(f"Executing trade for bot2: {signal}")



# # Worker for bot1_queue
# celery -A app worker --loglevel=info --concurrency=1 -Q bot1_queue

# # Worker for bot2_queue
# celery -A app worker --loglevel=info --concurrency=1 -Q bot2_queue

# # Worker for bot3_queue
# celery -A app worker --loglevel=info --concurrency=1 -Q bot3_queue