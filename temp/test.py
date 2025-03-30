import os
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import ta.momentum as momentum

# Load environment variables
load_dotenv()

# Gemini API Key and Base URL
API_KEY = os.getenv("GEMINI_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/"

# Initialize OpenAI (Gemini API)
client = OpenAI(api_key=str(API_KEY), base_url=BASE_URL)

def fetch_ohlcv(pair, granularity=86400, start=None, end=None):
    base_url = "https://api.exchange.coinbase.com/products"
    
    if not end:
        end = datetime.utcnow()
    if not start:
        start = end - timedelta(days=30)  # 30 days ago
    
    params = {
        "start": start.isoformat(timespec='seconds') + "Z",
        "end": end.isoformat(timespec='seconds') + "Z",
        "granularity": granularity
    }
    
    response = requests.get(f"{base_url}/{pair}/candles", params=params)
    
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {response.text}")
    
    data = response.json()
    
    df = pd.DataFrame(data, columns=["timestamp", "low", "high", "open", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='s')
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    return df

def add_technical_indicators(df):
    """Enhance the DataFrame with RSI, Moving Averages, and Candlestick color."""
    
    df["diff"] = df["close"] - df["open"]
    df["color"] = df["diff"].apply(lambda x: "green" if x >= 0 else "red")
    
    # Compute RSI
    df["rsi"] = momentum.rsi(df["close"], window=14, fillna=False)
    
    # Compute Moving Averages
    df["MA7"] = df["close"].rolling(window=7).mean()
    df["MA20"] = df["close"].rolling(window=20).mean()
    
    return df

def fetch_current_price(pair):
    """Fetch the current price of a cryptocurrency from Coinbase."""
    url = f"https://api.exchange.coinbase.com/products/{pair}/ticker"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise Exception(f"Error fetching price: {response.text}")
    
    return response.json().get("price")

def analyze_market_trend(pair, df):
    """Use Gemini AI to analyze market trends and suggest trading decisions."""
    
    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert in cryptocurrency trading. "
                    f"Analyze the provided OHLCV chart data for {pair} and suggest whether to buy, sell, or hold. "
                    "Consider RSI, Moving Averages, and candlestick patterns.\n\n"
                    "Provide your response in JSON format:\n"
                    "{\"decision\": \"buy\", \"reason\": \"some technical reason\"}\n"
                    "{\"decision\": \"sell\", \"reason\": \"some technical reason\"}\n"
                    "{\"decision\": \"hold\", \"reason\": \"some technical reason\"}"
                )
            },
            {
                "role": "user",
                "content": df.to_json(),
            },
        ]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    # Get user input for the coin pair
    coin_pair = input("Enter the coin pair (e.g., BTC-USD, ETH-USD): ")
    
    # Fetch and display 30 days of OHLCV data
    df = fetch_ohlcv(coin_pair)
    df = add_technical_indicators(df)  # Add indicators
    print(df.tail(30))  # Show last 30 rows with indicators
    
    # Get Gemini AI analysis
    decision = analyze_market_trend(coin_pair, df)
    print(f"Gemini AI Decision for {coin_pair}: {decision}")
    
    # Fetch real-time price every 5 seconds
    while True:
        price = fetch_current_price(coin_pair)
        print(f"Current {coin_pair} price: ${price}")
        time.sleep(5)
