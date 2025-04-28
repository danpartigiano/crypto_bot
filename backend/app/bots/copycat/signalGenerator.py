import redis
import logging
import time
import os
import sys, getopt
import json
import requests
from app.utility.environment import environment
from app.database.db_connection import context_get_session
from app.database.models import Subscription, Bot
from sqlalchemy.future import select


"""
SolanaCopyCatBot monitors a single top-performing Solana trader on the blockchain and copies their transactions.
It tracks a specific whale wallet address and generates trading signals based on their activity.
"""

# Logging per bot
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(os.path.basename(os.getcwd()))

# The target Solana trader wallet address to track
# In production, replace this with a real high-performing trader's address
TARGET_SOLANA_ADDRESS = "5jSb3rDQeFe4tyszrwU29F6u3Ysyq4G1YSarecR46FKQ"  # Example address

# Transaction cache to avoid duplicates
TRANSACTION_CACHE = set()

# API rate limiting
LAST_API_CALL = 0
MIN_API_INTERVAL = 60  # Seconds between API calls

def bot_worker(bot_id: int):
    """Main worker function that monitors a specific Solana whale trader"""

    redis_client = redis.StrictRedis(host=environment.REDIS_HOST, port=environment.REDIS_PORT, decode_responses=True)
    
    queue_name = f"bot{bot_id}_queue"

    # Remove any stale trades from the queue
    redis_client.delete(queue_name)

    logger.info(f"SolanaCopyCatBot {bot_id} started, monitoring Solana whale: {TARGET_SOLANA_ADDRESS}")
    
    # Initialize tracking
    initialize_trader_tracking(redis_client, bot_id)
    
    while True:
        try:
            # Find recent transactions from our target trader
            signals = check_solana_transactions(redis_client, bot_id)
            
            for signal in signals:
                redis_client.rpush(queue_name, signal)
                logger.info(f"SolanaCopyCatBot {bot_id} detected signal: {signal}")
            
            # Wait before checking again (respecting API rate limits)
            sleep_time = max(30, MIN_API_INTERVAL - (time.time() - LAST_API_CALL))
            time.sleep(sleep_time)
            
        except Exception as e:
            logger.error(f"Error in SolanaCopyCatBot {bot_id}: {e}")
            time.sleep(30)  # Wait before retrying after an error

def initialize_trader_tracking(redis_client, bot_id):
    """Initialize tracking for our target Solana trader"""
    
    # Get any existing trader info
    trader_info_json = redis_client.get(f"solana_copycat:{bot_id}:target_trader")
    
    if trader_info_json:
        trader_info = json.loads(trader_info_json)
        logger.info(f"Resuming tracking for Solana whale: {trader_info.get('sol_address', TARGET_SOLANA_ADDRESS)}")
    else:
        # Create new trader info
        trader_info = {
            "sol_address": TARGET_SOLANA_ADDRESS,
            "track_since": time.time(),
            "last_check_time": time.time(),
            "cumulative_profit": 0,
            "successful_trades": 0,
            "total_trades": 0,
            "last_transactions": []
        }
        
        # Save trader info to Redis
        redis_client.set(f"solana_copycat:{bot_id}:target_trader", json.dumps(trader_info))
        
        logger.info(f"Initialized tracking for Solana whale: {TARGET_SOLANA_ADDRESS}")
    
    # Initialize transaction history if it doesn't exist
    if not redis_client.exists(f"solana_copycat:{bot_id}:transaction_history"):
        redis_client.delete(f"solana_copycat:{bot_id}:transaction_history")

def check_solana_transactions(redis_client, bot_id):
    """Check for new Solana transactions from our target trader"""
    
    global LAST_API_CALL
    signals = []
    
    # Rate limiting
    current_time = time.time()
    if current_time - LAST_API_CALL < MIN_API_INTERVAL:
        return []
    
    try:
        # Get trader info from Redis
        trader_info_json = redis_client.get(f"solana_copycat:{bot_id}:target_trader")
        if not trader_info_json:
            logger.error("Trader info not found in Redis")
            return []
            
        trader_info = json.loads(trader_info_json)
        sol_address = trader_info.get("sol_address", TARGET_SOLANA_ADDRESS)
        last_check_time = trader_info.get("last_check_time", time.time() - 3600)
        
        logger.info(f"Checking for new Solana transactions from {sol_address}")
        
        # Update the last API call timestamp
        LAST_API_CALL = current_time
        
        # In production, here you would use a blockchain API to check for real transactions
        # Example APIs for Solana:
        # - Solana Explorer API
        # - Solscan API
        # - Solana Web3.js library
        
        # For a real implementation, you would query transaction history:
        # api_url = f"https://public-api.solscan.io/account/transactions?account={sol_address}&limit=20"
        # headers = {"accept": "application/json"}
        # response = requests.get(api_url, headers=headers)
        
        # if response.status_code == 200:
        #     txs = response.json()
        #     for tx in txs:
        #         # Process each transaction
        #         # Determine if it's a token swap/transfer and generate appropriate signals
        
        # For this example, we'll simulate finding transactions
        # Simulating 3 scenarios with different probabilities:
        # 1. No new transaction (70% probability)
        # 2. Buy transaction (21% probability - whales buy more often than sell)
        # 3. Sell transaction (9% probability)
        import random
        
        random_value = random.random()
        
        if random_value < 0.30:  # 30% chance to find a transaction
            # Generate a unique transaction ID
            tx_id = f"tx_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # Check if not already in cache
            if tx_id not in TRANSACTION_CACHE:
                # Add to cache
                TRANSACTION_CACHE.add(tx_id)
                
                # Determine transaction type (70% buy, 30% sell)
                if random_value < 0.21:  # 21% chance for buy
                    action = "BUY"
                else:  # 9% chance for sell
                    action = "SELL"
                
                # Create signal
                signal_id = int(time.time())
                signal = f"{signal_id}:{action}:SOL"
                signals.append(signal)
                
                # Record this transaction
                record_transaction(redis_client, bot_id, "SOL", action, tx_id)
        
        # Update the last check time
        trader_info["last_check_time"] = current_time
        redis_client.set(f"solana_copycat:{bot_id}:target_trader", json.dumps(trader_info))
        
    except Exception as e:
        logger.error(f"Error checking Solana transactions: {e}")
    
    return signals

def record_transaction(redis_client, bot_id, crypto, action, tx_hash):
    """Record a transaction from our target trader"""
    
    transaction = {
        "crypto": crypto,
        "action": action,
        "tx_hash": tx_hash,
        "timestamp": time.time(),
        "detected_at": time.time()
    }
    
    # Add to transaction history
    redis_client.lpush(f"solana_copycat:{bot_id}:transaction_history", json.dumps(transaction))
    
    # Keep only the most recent 100 transactions
    redis_client.ltrim(f"solana_copycat:{bot_id}:transaction_history", 0, 99)
    
    # Update trader stats
    trader_info_json = redis_client.get(f"solana_copycat:{bot_id}:target_trader")
    if trader_info_json:
        trader_info = json.loads(trader_info_json)
        trader_info["total_trades"] = trader_info.get("total_trades", 0) + 1
        
        # Keep track of last 10 transactions in trader info for quick reference
        last_transactions = trader_info.get("last_transactions", [])
        last_transactions.insert(0, {
            "crypto": crypto,
            "action": action,
            "timestamp": time.time()
        })
        trader_info["last_transactions"] = last_transactions[:10]  # Keep only last 10
        
        redis_client.set(f"solana_copycat:{bot_id}:target_trader", json.dumps(trader_info))
    
    logger.info(f"Recorded {action} transaction for {crypto} from target trader (TX: {tx_hash})")

def get_bot_id(argv):
    # Get bot id from command line
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
    logger.name = f"SolanaCopyCatBot {bot_id} generator"
    bot_worker(bot_id)

if __name__ == "__main__":
    main(get_bot_id(sys.argv[1:]))