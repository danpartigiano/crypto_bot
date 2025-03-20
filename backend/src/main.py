import asyncio
import json
import websockets
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException, Depends
import logging
from typing import Annotated
from pydantic import BaseModel
import models
from database import engine, get_db
from sqlalchemy.orm import Session

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

#create all of the tables and columns in our postgres DB
models.Base.metadata.create_all(bind=engine)

db_dependency = Annotated[Session, Depends(get_db)]

class LoginRequest(BaseModel):
    username: str
    password: str

# Coinbase WebSocket Info
URI = 'wss://ws-feed.exchange.coinbase.com'
CHANNEL = 'ticker'
PRODUCT_IDS = 'SOL-USD'

#TODO endpoints for logging into the site, this includes token making

#TODO endpoints to handle the OAuth from Coinbase or any other platform

#TODO priviledged endpoints to handle trading and other Coinbase account access 

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
    logger.debug("Recieved request for solana price websocket")
    await get_solana_price(websocket)

# Run the project with python main.py, this function will handle the rest
if __name__ == "__main__": 
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
