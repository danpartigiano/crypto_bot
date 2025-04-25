from app.utility.environment import environment
from app.utility.TokenService import TokenService
from app.database.db_connection import context_get_session
from app.database.models import Subscription, Bot
import redis
import logging
from sqlalchemy.future import select
import os
import sys, getopt
import json
import time


# Logging per bot
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(os.path.basename(os.getcwd()))


def execute_trades(bot_id: int):
    """Execute copied trades from a Bitcoin whale for all CopyCatBot subscribers"""

    redis_client = redis.StrictRedis(host=environment.REDIS_HOST, port=environment.REDIS_PORT, decode_responses=True)

    queue_name = f"bot{bot_id}_queue"

    logger.info(f"CopyCatBot executor for bot {bot_id} started, reading signals from {queue_name}")

    # Create a record in Redis for tracking trade history
    if not redis_client.exists(f"copycat:{bot_id}:trade_history"):
        redis_client.delete(f"copycat:{bot_id}:trade_history")

    while True:
        try:
            signal = redis_client.blpop(queue_name, timeout=10)

            if signal:
                _, trade_signal = signal  # Extract trade signal

                logger.info(f"Signal {trade_signal} being processed by CopyCatBot executor")

                # Record this trade in history
                record_trade(redis_client, bot_id, trade_signal)
                
                # Risk management check before executing trades
                if is_trade_safe(redis_client, bot_id, trade_signal):
                    process_trade_for_all(trade_signal, bot_id)
                else:
                    logger.warning(f"Trade {trade_signal} rejected by risk management")
                    # Update trade status to rejected
                    update_trade_status(redis_client, bot_id, trade_signal, "rejected")
            else:
                logger.info(f"No signals in {queue_name}, waiting...")

        except Exception as e:
            logger.error(f"Error in execute_trades for CopyCatBot {bot_id}: {e}")

def record_trade(redis_client, bot_id, trade_signal):
    """Record trade in history for performance tracking"""
    
    # Parse the signal
    try:
        signal_id, action, crypto = trade_signal.split(":")
    except ValueError:
        logger.error(f"Invalid signal format: {trade_signal}")
        return
    
    trade_data = {
        "signal": trade_signal,
        "signal_id": signal_id,
        "action": action,
        "crypto": crypto,
        "timestamp": time.time(),
        "status": "pending",
        "executions": []  # List to track executions for different users
    }
    
    # Add to a list of recent trades
    redis_client.lpush(f"copycat:{bot_id}:trade_history", json.dumps(trade_data))
    
    # Trim the list to keep only recent trades
    redis_client.ltrim(f"copycat:{bot_id}:trade_history", 0, 99)  # Keep last 100 trades

def is_trade_safe(redis_client, bot_id, trade_signal):
    """Perform risk management checks before executing a trade"""
    
    # Parse the signal
    try:
        signal_id, action, crypto = trade_signal.split(":")
    except ValueError:
        logger.error(f"Invalid signal format: {trade_signal}")
        return False
    
    # Ensure we're only dealing with Bitcoin
    if crypto != "BTC":
        logger.warning(f"Trade rejected: CopyCatBot only trades Bitcoin, not {crypto}")
        return False
    
    # Get recent trades
    recent_trades = redis_client.lrange(f"copycat:{bot_id}:trade_history", 0, 19)  # Last 20 trades
    
    # Count recent trades and their types
    trade_count = 0
    buy_count = 0
    sell_count = 0
    
    for trade_json in recent_trades:
        try:
            trade = json.loads(trade_json)
            if trade.get("crypto") == "BTC":
                trade_count += 1
                if trade.get("action") == "BUY":
                    buy_count += 1
                elif trade.get("action") == "SELL":
                    sell_count += 1
        except:
            pass
    
    # Risk management rules
    
    # 1. Limit frequency of trades
    if trade_count >= 6:  # No more than 6 trades in last 20 recorded signals
        recent_timestamps = [json.loads(t).get("timestamp", 0) for t in recent_trades[:6]]
        if min(recent_timestamps) > time.time() - 3600:  # All 6 happened within the last hour
            logger.warning("Trade rejected: Too many trades in the last hour")
            return False
    
    # 2. Implement a timeout between trades
    if recent_trades:
        try:
            last_trade = json.loads(recent_trades[0])
            last_trade_time = last_trade.get("timestamp", 0)
            
            # Require at least 10 minutes between trades
            if time.time() - last_trade_time < 600:
                logger.warning(f"Trade rejected: Minimum time between trades not met ({time.time() - last_trade_time} seconds)")
                return False
        except:
            pass
    
    # 3. Balance of buy/sell trades
    if action == "BUY" and buy_count > sell_count + 5:
        logger.warning("Trade rejected: Too many BUY orders without corresponding SELL orders")
        return False
    
    if action == "SELL" and sell_count > buy_count + 5:
        logger.warning("Trade rejected: Too many SELL orders without corresponding BUY orders")
        return False
    
    # 4. Market hours check (optional)
    current_hour = time.localtime().tm_hour
    if current_hour >= 22 or current_hour < 4:
        logger.warning("Trade rejected: Outside of active trading hours")
        return False
    
    return True

def process_trade_for_all(signal: str, bot_id: int):
    """Execute the trade for all subscribers of the CopyCatBot"""

    # Parse the signal
    try:
        signal_id, action, crypto = signal.split(":")
    except ValueError:
        logger.error(f"Invalid signal format: {signal}")
        return
    
    # Get all users subscribed to this bot
    with context_get_session() as db:
        subscriptions = db.scalars(select(Subscription).where(Subscription.bot_id == bot_id)).all()

        if not subscriptions:
            logger.warning(f"No subscribers found for bot {bot_id}")
            update_trade_status(redis_client, bot_id, signal, "skipped_no_subscribers")
            return

        logger.info(f"Processing {action} {crypto} trade for {len(subscriptions)} subscribers")
        
        # Get Redis client inside this function
        redis_client = redis.StrictRedis(host=environment.REDIS_HOST, port=environment.REDIS_PORT, decode_responses=True)

        successful_executions = 0
        failed_executions = 0

        for subscription in subscriptions:
            try:
                # Get this user's access token using TokenService
                token_service = TokenService(user_id=subscription.user_id, db=db)
                access_token = token_service.get_access_token(exchange_name="coinbase")
                
                if not access_token:
                    logger.error(f"No access token found for user {subscription.user_id}")
                    record_user_execution(redis_client, bot_id, signal, subscription.user_id, "failed", "No access token")
                    failed_executions += 1
                    continue

                # Execute the trade using Coinbase API
                result, message = execute_coinbase_trade(access_token, action, crypto, subscription.user_id)
                
                if result:
                    logger.info(f"Successfully executed {action} {crypto} trade for user {subscription.user_id}")
                    record_user_execution(redis_client, bot_id, signal, subscription.user_id, "completed", message)
                    successful_executions += 1
                else:
                    logger.warning(f"Failed to execute {action} {crypto} trade for user {subscription.user_id}: {message}")
                    record_user_execution(redis_client, bot_id, signal, subscription.user_id, "failed", message)
                    failed_executions += 1
                
            except Exception as e:
                logger.error(f"Failed to process {signal} for user {subscription.user_id}: {e}")
                record_user_execution(redis_client, bot_id, signal, subscription.user_id, "failed", str(e))
                failed_executions += 1
        
        # Update overall trade status
        if successful_executions > 0:
            if failed_executions == 0:
                update_trade_status(redis_client, bot_id, signal, "completed")
            else:
                update_trade_status(redis_client, bot_id, signal, "partially_completed")
        else:
            update_trade_status(redis_client, bot_id, signal, "failed")

def record_user_execution(redis_client, bot_id, signal, user_id, status, message=""):
    """Record the result of trade execution for a specific user"""
    
    # Find the trade in history
    recent_trades = redis_client.lrange(f"copycat:{bot_id}:trade_history", 0, 99)
    
    for i, trade_json in enumerate(recent_trades):
        trade = json.loads(trade_json)
        
        if trade.get("signal") == signal:
            # Add execution record
            execution = {
                "user_id": user_id,
                "status": status,
                "message": message,
                "timestamp": time.time()
            }
            
            # Update executions list
            executions = trade.get("executions", [])
            executions.append(execution)
            trade["executions"] = executions
            
            # Save updated trade
            redis_client.lset(f"copycat:{bot_id}:trade_history", i, json.dumps(trade))
            break

def update_trade_status(redis_client, bot_id, signal, status):
    """Update the status of a trade in the history"""
    
    # Get recent trades
    recent_trades = redis_client.lrange(f"copycat:{bot_id}:trade_history", 0, 99)
    
    for i, trade_json in enumerate(recent_trades):
        trade = json.loads(trade_json)
        
        if trade.get("signal") == signal:
            # Update status
            trade["status"] = status
            trade["updated_at"] = time.time()
            
            # Save updated trade
            redis_client.lset(f"copycat:{bot_id}:trade_history", i, json.dumps(trade))
            break

def execute_coinbase_trade(access_token, action, crypto, user_id):
    """Execute a trade on Coinbase using the user's access token"""
    
    try:
        # Import the coinbase client
        from coinbase.rest import Client
        
        # Create a client with the user's access token
        client = Client(access_token=access_token)
        
        # Set standard trade amount (in production, this could be configurable per user)
        # For safety, we'll use a small fixed amount
        trade_amount = 50.00  # $50 USD per trade
        
        # Get the user's accounts
        accounts = client.get_accounts()
        
        # Find the right account for Bitcoin
        btc_account = None
        usd_account = None
        
        for account in accounts.data:
            if account.currency.code == "BTC":
                btc_account = account
            elif account.currency.code == "USD":
                usd_account = account
        
        if not btc_account:
            # Create a new Bitcoin account if it doesn't exist
            btc_account = client.create_account(name="Bitcoin Wallet")
        
        if not usd_account:
            return False, "No USD account found"
        
        # Execute the trade
        if action == "BUY":
            # Check if user has enough USD
            usd_balance = float(usd_account.balance.amount)
            if usd_balance < trade_amount:
                return False, f"Insufficient USD balance: {usd_balance} < {trade_amount}"
                
            # Execute buy
            buy = client.buy(
                account_id=btc_account.id,
                amount=trade_amount,
                currency="USD",
                payment_method="USD Wallet"  # Use USD wallet as payment method
            )
            
            return bool(buy.id), f"Buy order executed: {buy.id}"
            
        elif action == "SELL":
            # Check if user has enough BTC to sell
            btc_balance = float(btc_account.balance.amount)
            
            # Get current price to calculate amount to sell
            price_data = client.get_spot_price(currency_pair="BTC-USD")
            btc_price = float(price_data.amount)
            
            btc_amount_to_sell = trade_amount / btc_price
            
            if btc_balance < btc_amount_to_sell:
                return False, f"Insufficient BTC balance: {btc_balance} < {btc_amount_to_sell}"
                
            # Execute sell
            sell = client.sell(
                account_id=btc_account.id,
                amount=btc_amount_to_sell,
                currency="BTC"
            )
            
            return bool(sell.id), f"Sell order executed: {sell.id}"
        
        return False, "Invalid action"
        
    except Exception as e:
        return False, f"Error executing Coinbase trade: {e}"

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
    logger.name = f"CopyCatBot {bot_id} executor"
    execute_trades(bot_id)

if __name__ == "__main__":
    main(get_bot_id(sys.argv[1:]))