import asyncio
import json
import websockets
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import logging
import joblib
import pandas as pd
import talib
import numpy as np

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

# Location of folder holding html files
templates = Jinja2Templates(directory="templates")

# Coinbase WebSocket Info
URI = 'wss://ws-feed.exchange.coinbase.com'
CHANNEL = 'ticker'
PRODUCT_IDS = 'SOL-USD'

# Load the trained model and scaler
model = joblib.load('sol_model.pkl')
scaler = joblib.load('scaler.pkl')

# Function to compute features from real-time data
def compute_features(df):
    df['sma_50'] = talib.SMA(df['close'], timeperiod=50)
    df['rsi'] = talib.RSI(df['close'], timeperiod=14)
    df['macd'], df['macd_signal'], _ = talib.MACD(df['close'])
    df['return_1h'] = df['close'].pct_change()
    return df

# Function to decide trading action based on prediction (to be tweaked with depending on scale of trades)
def decide_action(predicted_return, buy_threshold=0.02, sell_threshold=-0.02):
    if predicted_return > buy_threshold:
        return "buy"
    elif predicted_return < sell_threshold:
        return "sell"
    else:
        return "hold"

# Function to listen to the Coinbase WebSocket for real-time SOL price updates
async def get_solana_price(websocket: WebSocket):
    """Listen to the Coinbase WebSocket API to receive real-time price updates for Solana and send them to the client."""
    
    #subscribe to the coinbase websocket for solana
    subscribe_message = json.dumps({
        'type': 'subscribe',
        'channels': [{'name': CHANNEL, 'product_ids': [PRODUCT_IDS]}],
    })
    
    try:
        async with websockets.connect(URI, ping_interval=None) as ws:
            # subscribe to Coinbase feed
            await ws.send(subscribe_message)
            logger.info(f"Subscribed to Coinbase WebSocket for {PRODUCT_IDS}")

            while True:
                response = await ws.recv()
                json_response = json.loads(response)

                # get price data
                if 'price' in json_response:
                    price = json_response['price']
                    logger.debug(f"SOL-USD = {price}")

                    #TODO handle when client disconnects
                    await websocket.send_text(f"{price}")
                    
    #handle coinbase disconnect here - try to reconnect
    except websockets.exceptions.WebSocketException as e:
        print(e)


# WebSocket endpoint for SOL-USD price
@app.websocket("/ws/solana")
async def ws_solana(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    # Initialize DataFrame to store price history
    df = pd.DataFrame(columns=['timestamp', 'close'])
    
    while True:
        try:
            async with websockets.connect(URI, ping_interval=None) as ws:
                subscribe_message = json.dumps({
                    'type': 'subscribe',
                    'channels': [{'name': CHANNEL, 'product_ids': [PRODUCT_IDS]}],
                })
                await ws.send(subscribe_message)
                logger.info(f"Subscribed to Coinbase WebSocket for {PRODUCT_IDS}")

                while True:
                    response = await ws.recv()
                    json_response = json.loads(response)
                    if 'price' in json_response:
                        price = float(json_response['price'])
                        timestamp = pd.to_datetime(json_response['time'])
                        # Append new data to DataFrame
                        new_data = pd.DataFrame({'timestamp': [timestamp], 'close': [price]})
                        df = pd.concat([df, new_data], ignore_index=True)
                        df.set_index('timestamp', inplace=True)
                        # Limit DataFrame to last 50 entries for feature calculation
                        if len(df) > 50:
                            df = df.iloc[-50:]
                        # Compute features and make prediction
                        if len(df) >= 50:
                            df_features = compute_features(df.copy())
                            latest_features = df_features.iloc[-1][['sma_50', 'rsi', 'macd', 'macd_signal', 'return_1h']]
                            scaled_features = scaler.transform([latest_features])
                            predicted_return = model.predict(scaled_features)[0]
                            action = decide_action(predicted_return)
                            # Send price and action to client
                            await websocket.send_text(json.dumps({"price": price, "action": action}))
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except WebSocketDisconnect:
            logger.info("Client disconnected")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            break

# Serve the root page
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("/solana_real_time_price.html", {"request":request})

# Run the project with python main.py, this function will handle the rest
if __name__ == "__main__": 
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
