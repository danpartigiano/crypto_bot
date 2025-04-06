import ccxt
import pandas as pd
import talib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

# Fetch historical data from Binance
exchange = ccxt.kraken()
symbol = 'SOL/USDT' # Left for an example for now, to be selective later
timeframe = '1h'  # Hourly data
limit = 1000      # Last 1000 hours
ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# Feature engineering
df['sma_50'] = talib.SMA(df['close'], timeperiod=50)  # 50-period Simple Moving Average
df['rsi'] = talib.RSI(df['close'], timeperiod=14)     # Relative Strength Index
df['macd'], df['macd_signal'], _ = talib.MACD(df['close'])  # MACD
df['return_1h'] = df['close'].pct_change()           # 1-hour return
df = df.dropna()  # Remove rows with NaN values

# Define target: future return over the next 7 days (168 hours)
horizon = 7 * 24  # 7 days in hours
df['future_return'] = df['close'].shift(-horizon) / df['close'] - 1
df = df.dropna()

# Prepare features and target
features = ['sma_50', 'rsi', 'macd', 'macd_signal', 'return_1h']
X = df[features]
y = df['future_return']

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train the model (Random Forest Regression seems the best for the task)
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train_scaled, y_train)

# Save the trained model and scaler
joblib.dump(model, 'sol_model.pkl')
joblib.dump(scaler, 'scaler.pkl')

print("Model training completed and saved.")