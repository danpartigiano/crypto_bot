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
CopyCatBot monitors a single top-performing Bitcoin trader on the blockchain and copies their transactions.
It tracks a specific whale wallet address and generates trading signals based on their activity.
"""

# Logging per bot
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(os.path.basename(os.getcwd()))

# The target Bitcoin trader wallet address to track
# In production, replace this with a real high-performing trader's address
TARGET_BITCOIN_ADDRESS = "bc1q5mecc0lj3mehs6jrv0j830fyxdtqhpx9d9durh"  # Example address

# Transaction cache to avoid duplicates
TRANSACTION_CACHE = set()

# API rate limiting
LAST_API_CALL = 0
MIN_API_INTERVAL = 60  # Seconds between API calls

def bot_worker(bot_id: int):
    """Main worker function that monitors a specific Bitcoin whale trader"""

    redis_client = redis.StrictRedis(host=environment.REDIS_HOST, port=environment.REDIS_PORT, decode_responses=True)
    
    queue_name = f"bot{bot_id}_queue"

    # Remove any stale trades from the queue
    redis_client.delete(queue_name)

    logger.info(f"CopyCatBot {bot_id} started, monitoring Bitcoin whale: {TARGET_BITCOIN_ADDRESS}")
    
    # Initialize tracking
    initialize_trader_tracking(redis_client, bot_id)
    
    while True:
        try:
            # Find recent transactions from our target trader
            signals = check_bitcoin_transactions(redis_client, bot_id)
            
            for signal in signals:
                redis_client.rpush(queue_name, signal)
                logger.info(f"CopyCatBot {bot_id} detected signal: {signal}")
            
            # Wait before checking again (respecting API rate limits)
            sleep_time = max(30, MIN_API_INTERVAL - (time.time() - LAST_API_CALL))
            time.sleep(sleep_time)
            
        except Exception as e:
            logger.error(f"Error in CopyCatBot {bot_id}: {e}")
            time.sleep(30)  # Wait before retrying after an error

def initialize_trader_tracking(redis_client, bot_id):
    """Initialize tracking for our target Bitcoin trader"""
    
    # Get any existing trader info
    trader_info_json = redis_client.get(f"copycat:{bot_id}:target_trader")
    
    if trader_info_json:
        trader_info = json.loads(trader_info_json)
        logger.info(f"Resuming tracking for Bitcoin whale: {trader_info.get('btc_address', TARGET_BITCOIN_ADDRESS)}")
    else:
        # Create new trader info
        trader_info = {
            "btc_address": TARGET_BITCOIN_ADDRESS,
            "track_since": time.time(),
            "last_check_time": time.time(),
            "cumulative_profit": 0,
            "successful_trades": 0,
            "total_trades": 0,
            "last_transactions": []
        }
        
        # Save trader info to Redis
        redis_client.set(f"copycat:{bot_id}:target_trader", json.dumps(trader_info))
        
        logger.info(f"Initialized tracking for Bitcoin whale: {TARGET_BITCOIN_ADDRESS}")
    
    # Initialize transaction history if it doesn't exist
    if not redis_client.exists(f"copycat:{bot_id}:transaction_history"):
        redis_client.delete(f"copycat:{bot_id}:transaction_history")

def check_bitcoin_transactions(redis_client, bot_id):
    """Check for new Bitcoin transactions from our target trader"""
    
    global LAST_API_CALL
    signals = []
    
    # Rate limiting
    current_time = time.time()
    if current_time - LAST_API_CALL < MIN_API_INTERVAL:
        return []
    
    try:
        # Get trader info from Redis
        trader_info_json = redis_client.get(f"copycat:{bot_id}:target_trader")
        if not trader_info_json:
            logger.error("Trader info not found in Redis")
            return []
            
        trader_info = json.loads(trader_info_json)
        btc_address = trader_info.get("btc_address", TARGET_BITCOIN_ADDRESS)
        last_check_time = trader_info.get("last_check_time", time.time() - 3600)
        
        logger.info(f"Checking for new Bitcoin transactions from {btc_address}")
        
        # In production, here you would use a blockchain API to check for real transactions
        # Example APIs for Bitcoin:
        # - BlockCypher API: https://www.blockcypher.com/dev/bitcoin/
        # - Blockchain.info API: https://www.blockchain.com/api
        # - Blockstream API: https://github.com/Blockstream/esplora/blob/master/API.md
        
        # Update the last API call timestamp
        LAST_API_CALL = current_time
        
       
        # Get recent transactions
        api_url = f"https://api.blockcypher.com/v1/btc/main/addrs/{btc_address}/full"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            data = response.json()
            txs = data.get('txs', [])
            
            # Process each transaction
            for tx in txs:
                tx_hash = tx.get('hash')
                
                # Skip if we've already processed this transaction
                if tx_hash in TRANSACTION_CACHE:
                    continue
                    
                # Add to cache to avoid duplicates
                TRANSACTION_CACHE.add(tx_hash)
                
                # Get transaction timestamp
                tx_time = tx.get('received', '').replace('T', ' ').replace('Z', '')
                tx_timestamp = time.mktime(time.strptime(tx_time, '%Y-%m-%d %H:%M:%S'))
                
                # Skip old transactions
                if tx_timestamp < last_check_time:
                    continue
                
                # Determine if this is an incoming or outgoing transaction
                is_incoming = False
                is_outgoing = False
                
                for input_tx in tx.get('inputs', []):
                    if btc_address in input_tx.get('addresses', []):
                        is_outgoing = True
                        
                for output_tx in tx.get('outputs', []):
                    if btc_address in output_tx.get('addresses', []):
                        is_incoming = True
                
                # Generate trading signal based on transaction type
                if is_outgoing and not is_incoming:
                    # If the whale is sending BTC out, it might be selling
                    action = "SELL"
                elif is_incoming and not is_outgoing:
                    # If the whale is receiving BTC, it might be buying
                    action = "BUY"
                else:
                    # If it's a transfer between own wallets, ignore
                    continue
                
                # Create signal
                signal_id = int(time.time())
                signal = f"{signal_id}:{action}:BTC"
                signals.append(signal)
                
                # Record this transaction
                record_transaction(redis_client, bot_id, "BTC", action, tx_hash)

        
        # For this example, we'll simulate finding transactions (replace with real API in production)
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
                signal = f"{signal_id}:{action}:BTC"
                signals.append(signal)
                
                # Record this transaction
                record_transaction(redis_client, bot_id, "BTC", action, tx_id)
        
        # Update the last check time
        trader_info["last_check_time"] = current_time
        redis_client.set(f"copycat:{bot_id}:target_trader", json.dumps(trader_info))
        
    except Exception as e:
        logger.error(f"Error checking Bitcoin transactions: {e}")
    
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
    redis_client.lpush(f"copycat:{bot_id}:transaction_history", json.dumps(transaction))
    
    # Keep only the most recent 100 transactions
    redis_client.ltrim(f"copycat:{bot_id}:transaction_history", 0, 99)
    
    # Update trader stats
    trader_info_json = redis_client.get(f"copycat:{bot_id}:target_trader")
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
        
        redis_client.set(f"copycat:{bot_id}:target_trader", json.dumps(trader_info))
    
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
    logger.name = f"CopyCatBot {bot_id} generator"
    bot_worker(bot_id)

if __name__ == "__main__":
    main(get_bot_id(sys.argv[1:]))