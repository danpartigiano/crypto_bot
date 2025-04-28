import pandas as pd
import numpy as np
import joblib
import requests
from datetime import datetime, timedelta
import time
import os
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
from ta.volume import OnBalanceVolumeIndicator
import csv

# Paths to saved model files
MODEL_PATH = "data/solana_price_model.joblib"
SCALER_PATH = "data/solana_scaler.joblib"
RESULTS_PATH = "solana_backtest_results.csv"

# Trading parameters
INITIAL_CAPITAL = 10000.0  # $10,000 starting capital
BUY_THRESHOLD = 0.002      # 0.2% predicted increase for buy signal
SELL_THRESHOLD = -0.0015   # 0.15% predicted decrease for sell signal
POSITION_SIZE = 0.90       # Use 90% of available capital for each trade
TRADING_FEE = 0.001        # 0.1% trading fee

def fetch_historical_data(days=60):
    """Fetch historical price data for Solana from Coinbase API"""
    print(f"Fetching {days} days of historical Solana price data...")
    
    # Calculate time range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Format dates for Coinbase API
    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()
    
    all_candles = []
    
    # Coinbase limits to 300 data points per request, so we need to paginate
    # For hourly data (granularity=3600), we can fetch about 12.5 days at a time
    chunk_size = 10  # days per request
    
    # Process in chunks
    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=chunk_size), end_date)
        
        # Format dates for Coinbase API
        start_iso = current_start.isoformat()
        end_iso = current_end.isoformat()
        
        url = f"https://api.exchange.coinbase.com/products/SOL-USD/candles"
        params = {
            "start": start_iso,
            "end": end_iso,
            "granularity": 3600  # 1 hour intervals
        }
        
        print(f"Fetching chunk from {current_start.date()} to {current_end.date()}")
        headers = {
            "Accept": "application/json",
            "User-Agent": "SolanaMLBot/1.0"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                chunk_candles = response.json()
                all_candles.extend(chunk_candles)
                print(f"Successfully fetched {len(chunk_candles)} candles")
            else:
                print(f"API error: status {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"Error fetching data: {e}")
        
        # Move to next chunk
        current_start = current_end
        
        # Respect rate limits between chunks
        time.sleep(1)
    
    if all_candles:
        # Coinbase candle format: [timestamp, low, high, open, close, volume]
        # Convert to DataFrame
        df = pd.DataFrame(all_candles, columns=["timestamp", "low", "high", "open", "close", "volume"])
        
        # Convert timestamp to datetime and set as index
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df.set_index("timestamp", inplace=True)
        
        # Sort by timestamp (Coinbase returns newest first)
        df.sort_index(inplace=True)
        
        # Remove duplicates that might occur at chunk boundaries
        df = df[~df.index.duplicated(keep='first')]
        
        # Rename columns to match our expected format
        df.rename(columns={"close": "price"}, inplace=True)
        
        print(f"Successfully fetched all historical data: {len(df)} total candles")
        return df
    else:
        print("Failed to fetch any historical data")
        return None

def calculate_technical_indicators(df):
    """Calculate technical indicators for the ML model"""
    
    # Make a copy to avoid modifying the original
    df_indicators = df.copy()
    
    # Price transformation
    df_indicators["price_pct_change"] = df_indicators["price"].pct_change()
    df_indicators["log_return"] = np.log(df_indicators["price"] / df_indicators["price"].shift(1))
    
    # Moving averages
    df_indicators["sma_7"] = SMAIndicator(close=df_indicators["price"], window=7).sma_indicator()
    df_indicators["sma_25"] = SMAIndicator(close=df_indicators["price"], window=25).sma_indicator()
    df_indicators["ema_9"] = EMAIndicator(close=df_indicators["price"], window=9).ema_indicator()
    
    # MACD
    macd = MACD(close=df_indicators["price"])
    df_indicators["macd"] = macd.macd()
    df_indicators["macd_signal"] = macd.macd_signal()
    df_indicators["macd_diff"] = macd.macd_diff()
    
    # RSI
    df_indicators["rsi_14"] = RSIIndicator(close=df_indicators["price"], window=14).rsi()
    
    # Bollinger Bands
    bollinger = BollingerBands(close=df_indicators["price"])
    df_indicators["bollinger_mavg"] = bollinger.bollinger_mavg()
    df_indicators["bollinger_hband"] = bollinger.bollinger_hband()
    df_indicators["bollinger_lband"] = bollinger.bollinger_lband()
    df_indicators["bollinger_width"] = (df_indicators["bollinger_hband"] - df_indicators["bollinger_lband"]) / df_indicators["bollinger_mavg"]
    
    # Stochastic Oscillator
    stoch = StochasticOscillator(
        high=df_indicators["price"], 
        low=df_indicators["price"], 
        close=df_indicators["price"]
    )
    df_indicators["stoch_k"] = stoch.stoch()
    df_indicators["stoch_d"] = stoch.stoch_signal()
    
    # Volume indicators
    df_indicators["volume_pct_change"] = df_indicators["volume"].pct_change()
    df_indicators["on_balance_volume"] = OnBalanceVolumeIndicator(
        close=df_indicators["price"], 
        volume=df_indicators["volume"]
    ).on_balance_volume()
    
    # Price relative to moving averages
    df_indicators["price_sma_7_ratio"] = df_indicators["price"] / df_indicators["sma_7"]
    df_indicators["price_sma_25_ratio"] = df_indicators["price"] / df_indicators["sma_25"]
    
    # Volatility
    df_indicators["volatility_14"] = df_indicators["price_pct_change"].rolling(window=14).std()
    
    return df_indicators

def prepare_features(df):
    """Prepare features for prediction"""
    
    # Calculate indicators
    df_with_indicators = calculate_technical_indicators(df)
    
    # Drop NaN values
    df_with_indicators.dropna(inplace=True)
    
    # Target variable (future 5-hour return) - for backtesting comparison only
    df_with_indicators["actual_future_return"] = df_with_indicators["price"].pct_change(5).shift(-5)
    
    # Get feature columns (exclude price and target)
    feature_columns = [col for col in df_with_indicators.columns 
                      if col not in ["price", "actual_future_return"]]
    
    return df_with_indicators, feature_columns

def run_backtest():
    """Run a backtest of the trading strategy using the trained model"""
    
    print("Starting SolanaML backtest...")
    
    # Load trained model and scaler
    try:
        print(f"Loading model from {MODEL_PATH}")
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        print("Model and scaler loaded successfully")
    except Exception as e:
        print(f"Error loading model: {e}")
        return
    
    # Fetch historical data
    historical_data = fetch_historical_data(days=60)
    if historical_data is None or len(historical_data) < 30:
        print("Not enough historical data for backtest")
        return
    
    # Prepare features
    print("Calculating technical indicators...")
    data_with_features, feature_columns = prepare_features(historical_data)
    
    # Check if we have enough data after feature calculation
    if len(data_with_features) < 10:
        print("Not enough data after calculating features")
        return
    
    print(f"Prepared {len(data_with_features)} data points with {len(feature_columns)} features")
    
    # Initialize backtest variables
    portfolio_value = INITIAL_CAPITAL
    cash = INITIAL_CAPITAL
    shares = 0
    in_position = False
    entry_price = 0
    
    results = []
    
    # Process each time point in the data
    print("Running backtest simulation...")
    for i in range(len(data_with_features)):
        current_row = data_with_features.iloc[i]
        timestamp = current_row.name
        current_price = current_row["price"]
        
        # Skip if not enough history for features
        if i < 25:  # Arbitrary minimum for sufficient history
            continue
        
        # Get features for this time point
        features = current_row[feature_columns].values.reshape(1, -1)
        
        # Check model's expected features vs what we have
        expected_features = getattr(model, 'n_features_in_', None)
        if expected_features is not None and features.shape[1] != expected_features:
            # If we have too many features, trim to match the model
            if features.shape[1] > expected_features:
                features = features[:, :expected_features]
            else:
                print(f"Feature mismatch: Have {features.shape[1]}, need {expected_features}")
                continue
        
        # Scale features
        try:
            features_scaled = scaler.transform(features)
        except Exception as e:
            print(f"Error scaling features: {e}")
            continue
        
        # Make prediction
        try:
            prediction = model.predict(features_scaled)[0]
        except Exception as e:
            print(f"Error making prediction: {e}")
            continue
        
        # Determine trading action
        if not in_position and prediction > BUY_THRESHOLD:
            action = "BUY"
        elif in_position and prediction < SELL_THRESHOLD:
            action = "SELL"
        else:
            action = "HOLD"
        
        # Execute trading action
        trade_amount = 0
        trade_shares = 0
        
        if action == "BUY" and not in_position:
            # Calculate shares to buy (90% of cash)
            investment = cash * POSITION_SIZE
            trade_fee = investment * TRADING_FEE
            trade_shares = (investment - trade_fee) / current_price
            
            # Execute buy
            cash -= (trade_shares * current_price) + trade_fee
            shares = trade_shares
            entry_price = current_price
            in_position = True
            trade_amount = investment
            
        elif action == "SELL" and in_position:
            # Execute sell
            sale_value = shares * current_price
            trade_fee = sale_value * TRADING_FEE
            cash += sale_value - trade_fee
            
            trade_amount = sale_value
            trade_shares = shares
            shares = 0
            in_position = False
        
        # Calculate current portfolio value
        portfolio_value = cash + (shares * current_price)
        
        # Record result
        actual_future_return = current_row.get("actual_future_return", np.nan)
        
        result = {
            "timestamp": timestamp,
            "price": current_price,
            "prediction": prediction,
            "action": action,
            "trade_amount": trade_amount,
            "trade_shares": trade_shares,
            "shares_held": shares,
            "cash": cash,
            "portfolio_value": portfolio_value,
            "in_position": in_position,
            "actual_future_return": actual_future_return
        }
        
        results.append(result)
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    # Calculate performance metrics
    initial_value = INITIAL_CAPITAL
    final_value = results_df["portfolio_value"].iloc[-1]
    total_return = (final_value - initial_value) / initial_value
    
    n_days = (results_df["timestamp"].iloc[-1] - results_df["timestamp"].iloc[0]).total_seconds() / (24 * 3600)
    annualized_return = ((1 + total_return) ** (365 / n_days)) - 1
    
    buy_trades = results_df[results_df["action"] == "BUY"]
    sell_trades = results_df[results_df["action"] == "SELL"]
    n_trades = len(buy_trades)
    
    # Calculate drawdown
    results_df["peak_value"] = results_df["portfolio_value"].cummax()
    results_df["drawdown"] = 1 - results_df["portfolio_value"] / results_df["peak_value"]
    max_drawdown = results_df["drawdown"].max()
    
    # Calculate daily returns
    results_df["daily_return"] = results_df["portfolio_value"].pct_change(24)  # 24 hours
    daily_returns = results_df["daily_return"].dropna()
    
    # Calculate Sharpe ratio (assuming risk-free rate of 0 for simplicity)
    if len(daily_returns) > 0:
        sharpe_ratio = np.sqrt(365) * (daily_returns.mean() / daily_returns.std())
    else:
        sharpe_ratio = np.nan
    
    # Calculate win rate
    if n_trades > 0:
        # Match buys with subsequent sells to determine if trades were profitable
        trade_pnl = []
        buy_index = 0
        
        for i, sell in sell_trades.iterrows():
            if buy_index < len(buy_trades):
                buy = buy_trades.iloc[buy_index]
                buy_price = buy["price"]
                sell_price = sell["price"]
                pnl = (sell_price - buy_price) / buy_price
                trade_pnl.append(pnl)
                buy_index += 1
        
        winning_trades = sum(1 for pnl in trade_pnl if pnl > 0)
        win_rate = winning_trades / len(trade_pnl) if trade_pnl else 0
    else:
        win_rate = np.nan
    
    # Print summary
    print("\nBacktest Results Summary:")
    print(f"Testing Period: {results_df['timestamp'].iloc[0]} to {results_df['timestamp'].iloc[-1]}")
    print(f"Initial Capital: ${initial_value:.2f}")
    print(f"Final Portfolio Value: ${final_value:.2f}")
    print(f"Total Return: {total_return:.2%}")
    print(f"Annualized Return: {annualized_return:.2%}")
    print(f"Number of Trades: {n_trades}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Maximum Drawdown: {max_drawdown:.2%}")
    print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    
    # Save results to CSV
    print(f"\nSaving results to {RESULTS_PATH}")
    results_df.to_csv(RESULTS_PATH)
    
    # Save performance summary
    with open("solana_backtest_summary.csv", "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Initial Capital", f"${initial_value:.2f}"])
        writer.writerow(["Final Portfolio Value", f"${final_value:.2f}"])
        writer.writerow(["Total Return", f"{total_return:.2%}"])
        writer.writerow(["Annualized Return", f"{annualized_return:.2%}"])
        writer.writerow(["Number of Trades", n_trades])
        writer.writerow(["Win Rate", f"{win_rate:.2%}"])
        writer.writerow(["Maximum Drawdown", f"{max_drawdown:.2%}"])
        writer.writerow(["Sharpe Ratio", f"{sharpe_ratio:.2f}"])
    
    print("Backtest completed successfully!")
    
    return results_df

if __name__ == "__main__":
    run_backtest()