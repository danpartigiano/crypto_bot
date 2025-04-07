import os
from dotenv import load_dotenv
import json
import websockets
import uvicorn
import requests
import logging
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from jwt.exceptions import JWTException
from fastapi import FastAPI, WebSocket, HTTPException, Depends, status, Request, APIRouter
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

from fastapi.middleware.cors import CORSMiddleware


# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

#connection with frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#create all of the tables and columns in our postgres DB
models.Base.metadata.create_all(bind=engine)

db = Annotated[Session, Depends(get_db)]

#load the environment variables
load_dotenv()

#Coinbase Variables
COINBASE_CLIENT_ID = os.getenv("COINBASE_CLIENT_ID")
COINBASE_CLIENT_SECRET = os.getenv("COINBASE_CLIENT_SECRET")
COINBASE_REDIRECT_URI = os.getenv("COINBASE_REDIRECT_URI")

router = APIRouter()

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

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password):
        return user
    return None

def create_access_token(data: dict, secret_key: str, algorithm: str):
    expiration = timedelta(hours=1)  # Token expiration time (1 hour)
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + expiration})
    
    # Encode the JWT token
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)

def validate_jwt(token: str):
    # Ensure the token has the correct number of segments
    if len(token.split('.')) != 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token format")

def get_current_user(db: Session, token: str):
    try:
        # Validate token format
        validate_jwt(token)

        # Decode the token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is invalid")
        user = db.query(models.User).filter(models.User.username == username).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Token decoding error: {str(e)}")

def generate_state() -> str:
    return secrets.token_urlsafe(16)

def get_oauth_from_state(db: Session, state: str) -> OAuth_State:
    return db.query(OAuth_State).filter(OAuth_State.state == state).first()

#-------------------------------------------------------------------------------------

@app.get("/coinbase/url", summary="Returns URL to Coinbase to initiate oauth")
async def login_coinbase(db: Annotated[Session, Depends(get_db)], token: Annotated[str, Depends(oauth2_scheme)]):
    
    # verify the current user
    user_data = get_current_user(db, token)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Token"
        )

    #generate the state
    state = generate_state()

    #construct the url
    coinbase_auth_url = f"{OAUTH_URL}?client_id={COINBASE_CLIENT_ID}&redirect_uri={COINBASE_REDIRECT_URI}&response_type=code&scope={SCOPE}&state={state}"


    # Store the state in the database if you want to track it (Optional)
    new_oauth_model = OAuth_State(state=state)
    try:
        db.add(new_oauth_model)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error saving state to database: {str(e)}")
    
    return JSONResponse(content={"coinbase_url": coinbase_auth_url})


@app.get("/coinbase/callback", summary="Coinbase redirect route")
async def coinbase_callback(db: Annotated[Session, Depends(get_db)], request: Request):
    """
    Coinbase redirects to this route after the user logs in and authorizes the app.
    We exchange the authorization code for an access token, and then fetch the username.
    """

    # Validate the state parameter here (optional but recommended)

    # Extract the authorization code and state from the query parameters
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # 1. Exchange the code for an access token
    token_url = "https://api.coinbase.com/oauth/token"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": COINBASE_CLIENT_ID,
        "client_secret": COINBASE_CLIENT_SECRET,
        "redirect_uri": COINBASE_REDIRECT_URI
    }

    token_response = requests.post(token_url, data=token_data)
    if token_response.status_code != 200:
        raise HTTPException(status_code=token_response.status_code, detail="Failed to fetch token")

    token_info = token_response.json()
    access_token = token_info.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to get access token")

    # 2. Fetch the user's Coinbase account info (e.g., username)
    user_info_url = "https://api.coinbase.com/v2/user"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_response = requests.get(user_info_url, headers=headers)

    if user_response.status_code != 200:
        raise HTTPException(status_code=user_response.status_code, detail="Failed to fetch user info")

    user_info = user_response.json()
    username = user_info['data']['name']  # Get the user's name from Coinbase

    # 3. Store the user info in your database (e.g., username)
    # Assuming you have a model like 'User' for storing the information
    new_user = User(username=username, coinbase_access_token=access_token)
    try:
        db.add(new_user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error storing user info: {str(e)}")

    # 4. Redirect the user to a success page or back to the frontend
    return RedirectResponse(url=f"http://localhost:3000/callback?username={username}")  # Example frontend success page

@app.post('/user/login', summary="Create access token for user")
async def login(db: Annotated[Session, Depends(get_db)], form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    
    user = authenticate_user(db, form_data.username, form_data.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        {"sub": user.username},  # Data to encode in the token
        secret_key=JWT_SECRET_KEY,  # Secret key for encoding
        algorithm=ALGORITHM  # Algorithm used to encode
    )

    return {"access_token": access_token, "token_type": "bearer"}

@app.post('/user/signup', summary="Create new platform user", response_model=UserOut, status_code=status.HTTP_201_CREATED)
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

#Trade execution
@app.post("/api/trade")
async def execute_trade(data: dict, db: Session = Depends(get_db)):
    
    crypto_pair = data.get("cryptoPair")
    amount = data.get("amount")
    if not crypto_pair or not amount:
        raise HTTPException(status_code=400, detail="Invalid data")

   
    status = "success" 

    
    return {"status": status}

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
