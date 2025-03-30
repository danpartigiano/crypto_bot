import os
from dotenv import load_dotenv
import json
import websockets
import uvicorn

from fastapi import FastAPI, WebSocket, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import User
from app.services.database import SessionLocal, engine, get_db
from utils import get_password_hash, create_access_token, create_refresh_token, authenticate_user, decode_refresh_token
from schemas import UserAuth, UserOut, Token
import models
import logging
from typing import Annotated


# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

#create all of the tables and columns in our postgres DB
models.Base.metadata.create_all(bind=engine)

db_dependency = Annotated[Session, Depends(get_db)]


@app.post('/refresh-token', summary="Refresh access token", response_model=Token)
async def refresh_token(db: db_dependency, refresh_token: str):
    
    user_id, username = decode_refresh_token(refresh_token)

    if user_id is None or username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Create new access token
    new_access_token = create_access_token(user.username, user.id)

    return Token(access_token=new_access_token, refresh_token=refresh_token)

@app.post('/login', summary="Create access and refresh tokens for user", response_model=Token)
async def login(db: db_dependency, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    
    user = authenticate_user(form_data.username, form_data.password, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )

    return Token(access_token=create_access_token(user.username, user.id), refresh_token=create_refresh_token(user.username, user.id))

@app.post('/signup', summary="Create new platform user", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, data: UserAuth):

    hashed_password = get_password_hash(data.password)
    new_user_model = User(username=data.username, email=data.email, hashed_password=hashed_password)
    try:
        db.add(new_user_model)
        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exist"
        )
    return UserOut(username=data.username, email=data.email)

# Coinbase WebSocket Info
URI = 'wss://ws-feed.exchange.coinbase.com'
CHANNEL = 'ticker'
PRODUCT_IDS = 'SOL-USD'


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

    #Check for required environment variables

    ALGORITHM = os.environ['ALGORITHM']
    JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']
    JWT_REFRESH_SECRET_KEY = os.environ['JWT_REFRESH_SECRET_KEY']

    if ALGORITHM is None or JWT_SECRET_KEY is None or JWT_REFRESH_SECRET_KEY is None:
        logger.error("You need to establish the required environment variables")
        exit(1)

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
