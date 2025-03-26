import os
from dotenv import load_dotenv
import json
import websockets
import uvicorn
import requests
import logging
from datetime import datetime, timedelta, timezone
from jose import jwt
from jwt.exceptions import JWTException
from fastapi import FastAPI, WebSocket, HTTPException, Depends, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import User, OAuth_State
from database import SessionLocal, engine, get_db
from schemas import UserAuth, UserOut, Token
import models
from typing import Annotated, Union, Any
import bcrypt
import secrets


# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

#create all of the tables and columns in our postgres DB
models.Base.metadata.create_all(bind=engine)

db = Annotated[Session, Depends(get_db)]

#load the environment variables
load_dotenv()

#Coinbase Variables
COINBASE_CLIENT_ID = os.getenv("COINBASE_CLIENT_ID")
COINBASE_CLIENT_SECRET = os.getenv("COINBASE_CLIENT_SECRET")
COINBASE_REDIRECT_URI = os.getenv("COINBASE_REDIRECT_URI")
OAUTH_URL = "https://www.coinbase.com/oauth/authorize"
TOKEN_URL = "https://api.coinbase.com/oauth/token"
SCOPE = "wallet:transactions:read wallet:accounts:read wallet:orders:create"

#Authentication Variables
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ALGORITHM = os.environ['ALGORITHM']
JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY'] 

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

#Helper Functions -------------------------------------------------------------------

def get_password_hash(password: str) -> str:
    '''Generates the hash of the given password'''
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt)

def verify_password(password: str, hashed_password: str) -> bool:
    '''Verifies if the given password matches the given hash'''
    password_bytes = password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password)

def get_user_by_username(db: Session, username: str) -> Union[User, None]:
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db: Session, id: int) -> Union[User, None]:
    return db.query(User).filter(User.id == id).first()

def authenticate_user(db: Session, username: str, password: str) -> Union[User, None]:
    user = get_user_by_username(db, username)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(username: str, user_id: int, expires_delta: timedelta | None = None) -> str:

    if expires_delta is not None:
        expires_delta = datetime.now(timezone.utc) + expires_delta
    else:
        expires_delta = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": username, "id" : user_id}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)
    return encoded_jwt

async def get_current_user(db: Session, token: Annotated[str, Depends(oauth2_scheme)]) -> Union[User, None]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, ALGORITHM)
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        user = get_user_by_username(db, username=username)
        if user is None:
            raise credentials_exception
        return user
    except JWTException:
        raise credentials_exception

def generate_state() -> str:
    return secrets.token_urlsafe(16)

def get_oauth_from_state(db: Session, state: str) -> OAuth_State:
    return db.query(OAuth_State).filter(OAuth_State.state == state).first()

#-------------------------------------------------------------------------------------

@app.get("/coinbase/url", summary="Returns URL to Coinbase to initiate oauth")
async def login_coinbase(db: Annotated[Session, Depends(get_db)], token: Annotated[str, Depends(oauth2_scheme)]):
    
    #verify the current user
    user_data = await get_current_user(db, token)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Token"
        )

    #generate the state
    state = generate_state()

    #construct the url
    coinbase_auth_url = f"{OAUTH_URL}?client_id={COINBASE_CLIENT_ID}&redirect_uri={COINBASE_REDIRECT_URI}&response_type=code&scope={SCOPE}&state={state}"


    #build the response
    content = {"coinbase_url": coinbase_auth_url}
    response = JSONResponse(content=content)
    response.set_cookie(key="state", value=state)

    #link the state to the current user in the database
    new_oauth_model = OAuth_State(state=state, user_id=user_data.id)

    try:
        db.add(new_oauth_model)
        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can't link user to state"
        )
    
    return response

@app.get("/coinbase/callback", summary="Coinbase redirect route")
async def login_coinbase(db: Annotated[Session, Depends(get_db)], request: Request):

    state_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate state",
    )

    #retrieve all data from the request
    state_cookie = request.cookies.get("state")
    state_url = request.query_params.get("state")

    if state_cookie is None or state_url is None or state_url != state_cookie:
        raise state_exception
    
    oauth = get_oauth_from_state(db, state_cookie)

    if oauth is None:
        raise state_exception

    state_db = oauth.state

    user_data = get_user_by_id(db, id=oauth.user_id)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_UNAUTHORIZED,
            detail="User not found",
        )
    
    #get the coinbase code
    code = request.query_params.get("code")

    if code is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No code from Coinbase found",
        )


    content = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": COINBASE_REDIRECT_URI,
        "client_id": COINBASE_CLIENT_ID,
        "client_secret": COINBASE_CLIENT_SECRET
    }

    response = requests.post(TOKEN_URL, data=content)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to get access tokens from coinbase",
        )

    #TODO store the tokens securely using another encryption key, for now just send back whether or not this was successful
    #TODO delete the entry in OAUTH for this user, it will never be used again and we don't want to double up on states


    return {"status": "success"}

@app.post('/login', summary="Create access token for user")
async def login(db: Annotated[Session, Depends(get_db)], form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    
    user = authenticate_user(db, form_data.username, form_data.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token=create_access_token(user.username, user.id)

    return Token(access_token=access_token, token_type="bearer")

@app.post('/signup', summary="Create new platform user", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(db: Annotated[Session, Depends(get_db)], data: UserAuth):

    hashed_password = get_password_hash(data.password)
    new_user_model = User(username=data.username, email=data.email, hashed_password=hashed_password)
    try:
        db.add(new_user_model)
        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username or email already exist"
        )
    return UserOut(username=data.username, email=data.email)

# Coinbase WebSocket Info
URI = 'wss://ws-feed.exchange.coinbase.com'
CHANNEL = 'ticker'
PRODUCT_IDS = 'SOL-USD'

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

    print("You need to establish the required environment variables in a .env file")
    print("the variables are: ALGORITHM, JWT_SECRET_KEY, JWT_REFRESH_SECRET_KEY, COINBASE_CLIENT_ID, COINBASE_CLIENT_SECRET, COINBASE_REDIRECT_URI")

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
