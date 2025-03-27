import os
from dotenv import load_dotenv
import json
import websockets
import uvicorn
import requests
import logging
from datetime import datetime, timedelta, timezone
from jose import jwt
from jose.exceptions import JWTError
from fastapi import FastAPI, WebSocket, HTTPException, Depends, status, Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import User
from database import SessionLocal, engine, get_db
from schemas import UserAuth, UserOut, Token
import models
from typing import Annotated, Union
import bcrypt

# NEW IMPORTS FOR MODEL INFERENCE
import ccxt
import pandas as pd
import talib
import joblib

# NEW IMPORT: Coinbase Advanced REST Client
from coinbase.rest import RESTClient

# Load environment variables
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

# (Optional) Enable CORS if needed for your frontend
# from fastapi.middleware.cors import CORSMiddleware
# origins = ["http://localhost:3000"]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Create all tables in the Postgres DB
models.Base.metadata.create_all(bind=engine)

db = Annotated[Session, Depends(get_db)]

# Authentication Variables
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ALGORITHM = os.environ["ALGORITHM"]
JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# -----------------------------------------
# Helper Functions (Authentication, etc.)
# -----------------------------------------
def get_password_hash(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt)

def verify_password(password: str, hashed_password: str) -> bool:
    password_bytes = password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_password)

def get_user(db: Session, username: str) -> Union[User, None]:
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str) -> Union[User, None]:
    user = get_user(db, username)
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
    to_encode = {"exp": expires_delta, "sub": username, "id": user_id}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)
    return encoded_jwt

async def get_current_user(db: Session, token: Annotated[str, Depends(oauth2_scheme)]) -> Union[User, None]:
    # For testing purposes: bypass JWT if using a placeholder token.
    if token == "YOUR_TEST_ACCESS_TOKEN":
        test_user = db.query(User).first()
        if not test_user:
            dummy_password = bcrypt.hashpw("testpassword".encode("utf-8"), bcrypt.gensalt())
            test_user = User(username="testuser", email="test@example.com", hashed_password=dummy_password)
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        return test_user
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        user = get_user(db, username=username)
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception

# -----------------------------------------
# Load Trained Model and Scaler Globally
# -----------------------------------------
try:
    model = joblib.load("sol_model.pkl")
    scaler = joblib.load("scaler.pkl")
    logger.info("Trained model and scaler loaded successfully.")
except Exception as e:
    logger.error(f"Error loading model/scaler: {e}")
    model = None
    scaler = None

# -----------------------------------------
# Decision Model Functions
# -----------------------------------------
def fetch_historical_data() -> pd.DataFrame:
    exchange = ccxt.kraken()
    symbol = "SOL/USDT"
    timeframe = "1h"
    limit = 1000
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df

def decision_model() -> tuple[str, float, float]:
    if model is None or scaler is None:
        raise Exception("Model or scaler not loaded.")
    df = fetch_historical_data()
    df["sma_50"] = talib.SMA(df["close"], timeperiod=50)
    df["rsi"] = talib.RSI(df["close"], timeperiod=14)
    macd, macd_signal, _ = talib.MACD(df["close"])
    df["macd"] = macd
    df["macd_signal"] = macd_signal
    df["return_1h"] = df["close"].pct_change()
    df = df.dropna()
    features = ["sma_50", "rsi", "macd", "macd_signal", "return_1h"]
    current_features = df[features].iloc[-1:]
    current_price = df["close"].iloc[-1]
    scaled_features = scaler.transform(current_features)
    predicted_return = model.predict(scaled_features)[0]
    threshold_buy = 0.01
    threshold_sell = -0.01
    if predicted_return > threshold_buy:
        decision = "buy"
    elif predicted_return < threshold_sell:
        decision = "sell"
    else:
        decision = "hold"
    return decision, predicted_return, current_price

# -----------------------------------------
# Trade Execution Function (using coinbase-advanced-py)
# -----------------------------------------
def execute_trade(decision: str, amount: float, price: float) -> dict:
    """
    Execute a trade using coinbase-advanced-py.
    For a market buy, we specify funds (USD) to spend.
    For a market sell, we specify size (SOL) to sell.
    """
    try:
        client = RESTClient(
            api_key=os.getenv("CDP_API_KEY"),
            api_secret=os.getenv("CDP_API_SECRET"),
            # Optionally, you can add timeout or rate_limit_headers parameters
        )
        product_id = "SOL-USD"
        if decision == "buy":
            # Place a market order to buy SOL using USD funds.
            order = client.market_order_buy(
                client_order_id="",  # Empty string to auto-generate a unique ID.
                product_id=product_id,
                quote_size=str(amount)  # USD amount to spend.
            )
        elif decision == "sell":
            # Retrieve the available SOL balance from the SOL account
            accounts = client.get_accounts()
            sol_balance = None
            for acct in accounts.accounts:
                # Check if the account currency is SOL (case-insensitive)
                if acct.currency.upper() == "SOL":
                    sol_balance = acct.available_balance.get("value")
                    break
            if sol_balance is None:
                return {"error": "No SOL account found or balance unavailable"}
            # Place a market sell order using the entire SOL balance
            order = client.market_order_sell(
                client_order_id="",
                product_id=product_id,
                base_size=str(0.001)  # Sell the entire available SOL
            )
        else:
            return {"status": "No trade executed", "detail": "Decision was hold"}
        # Convert the response to a dictionary (if available).
        return order.to_dict() if hasattr(order, "to_dict") else {"order": str(order)}
    except Exception as e:
        logger.error(f"Trade execution failed: {e}")
        return {"error": str(e)}

# -----------------------------------------
# Routes
# -----------------------------------------
@app.get("/coinbase/login", summary="Client login to Coinbase")
async def login_coinbase(db: Annotated[Session, Depends(get_db)], token: Annotated[str, Depends(oauth2_scheme)]):
    user_data = await get_current_user(db, token)
    if user_data is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    auth_url = f"https://www.coinbase.com/oauth/authorize?client_id={os.getenv('COINBASE_CLIENT_ID')}&redirect_uri={os.getenv('COINBASE_REDIRECT_URI')}&response_type=code&scope=wallet:transactions:read wallet:accounts:read wallet:orders:create"
    return RedirectResponse(auth_url)

@app.get("/coinbase/redirect", summary="Coinbase redirect route")
async def coinbase_redirect(request: Request, db: Annotated[Session, Depends(get_db)], token: Annotated[str, Depends(oauth2_scheme)]):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code in query parameters")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": os.getenv("COINBASE_CLIENT_ID"),
        "client_secret": os.getenv("COINBASE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("COINBASE_REDIRECT_URI"),
    }
    response = requests.post("https://api.coinbase.com/oauth/token", data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Failed to exchange code for token: {response.text}")
    token_data = response.json()
    user = await get_current_user(db, token)
    user.coinbase_access_token = token_data.get("access_token")
    user.coinbase_refresh_token = token_data.get("refresh_token")
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating user: {e}")
    return {"detail": "Coinbase account successfully linked.", "coinbase_token_data": token_data}

@app.post("/login", summary="Create access token for user")
async def login(db: Annotated[Session, Depends(get_db)], form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(user.username, user.id)
    return Token(access_token=access_token, token_type="bearer")

@app.post("/signup", summary="Create new platform user", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(db: Annotated[Session, Depends(get_db)], data: UserAuth):
    hashed_password = get_password_hash(data.password)
    new_user_model = User(username=data.username, email=data.email, hashed_password=hashed_password)
    try:
        db.add(new_user_model)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this username or email already exists")
    return UserOut(username=data.username, email=data.email)

# Coinbase WebSocket for SOL-USD price updates
URI = "wss://ws-feed.exchange.coinbase.com"
CHANNEL = "ticker"
PRODUCT_IDS = "SOL-USD"

async def get_solana_price(websocket: WebSocket):
    subscribe_message = json.dumps({
        "type": "subscribe",
        "channels": [{"name": CHANNEL, "product_ids": [PRODUCT_IDS]}],
    })
    try:
        async with websockets.connect(URI, ping_interval=None) as ws:
            await ws.send(subscribe_message)
            logger.info(f"Subscribed to Coinbase WebSocket for {PRODUCT_IDS}")
            while True:
                response = await ws.recv()
                json_response = json.loads(response)
                if "price" in json_response:
                    price = json_response["price"]
                    logger.debug(f"SOL-USD = {price}")
                    await websocket.send_text(f"{price}")
    except websockets.exceptions.WebSocketException as e:
        logger.error(f"WebSocket exception: {e}")

@app.websocket("/ws/solana")
async def ws_solana(websocket: WebSocket):
    await websocket.accept()
    logger.debug("Received request for Solana price websocket")
    await get_solana_price(websocket)

@app.post("/trade", summary="Evaluate decision and execute trade on Coinbase")
async def trade_execution(db: Annotated[Session, Depends(get_db)], token: Annotated[str, Depends(oauth2_scheme)]):
    user = await get_current_user(db, token)
    try:
        decision, predicted_return, current_price = decision_model()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decision model error: {e}")
    if decision == "hold":
        return {
            "decision": decision,
            "predicted_return": predicted_return,
            "current_price": current_price,
            "message": "Holding position. No trade executed."
        }
    trade_amount = 1  # Adjust the trade amount as needed
    trade_response = execute_trade(decision, trade_amount, current_price)
    return {
        "decision": decision,
        "predicted_return": predicted_return,
        "current_price": current_price,
        "trade_response": trade_response
    }

# Serve a simple HTML front-end at "/"
@app.get("/", response_class=HTMLResponse, summary="Front-end for Crypto Bot")
async def root():
    html_content = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Crypto Bot Trade Decision</title>
        <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
      </head>
      <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 50px;">
        <h1>Crypto Bot Trade Decision</h1>
        <button id="tradeButton" style="padding: 10px 20px; font-size: 16px;">Get Trade Decision</button>
        <div id="result" style="margin-top: 20px;"></div>
        <script>
          document.getElementById("tradeButton").addEventListener("click", async function() {
            try {
              const token = "YOUR_TEST_ACCESS_TOKEN"; // Replace with a valid JWT for production
              const response = await axios.post("http://127.0.0.1:8000/trade", {}, {
                headers: {
                  "Authorization": `Bearer ${token}`
                }
              });
              const data = response.data;
              document.getElementById("result").innerHTML = `
                <h2>Decision: ${data.decision}</h2>
                <p>Predicted Return: ${data.predicted_return}</p>
                <p>Current Price: ${data.current_price}</p>
                <pre style="text-align: left;">Trade Response: ${JSON.stringify(data.trade_response, null, 2)}</pre>
              `;
            } catch (err) {
              console.error(err);
              document.getElementById("result").innerHTML = "<p style='color:red;'>Error: " + (err.response ? err.response.data.detail : err.message) + "</p>";
            }
          });
        </script>
      </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    print("Ensure you have established the required environment variables in your .env file:")
    print("ALGORITHM, JWT_SECRET_KEY, COINBASE_ADVANCED_API_KEY, COINBASE_ADVANCED_API_SECRET")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)