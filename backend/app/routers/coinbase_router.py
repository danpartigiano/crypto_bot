from fastapi import APIRouter, HTTPException, status, Request, Depends, WebSocket, WebSocketDisconnect
from app.utility import user_helper, coinbase_helper
from sqlalchemy.orm import Session
from app.database.db_connection import get_session
from fastapi.responses import JSONResponse, HTMLResponse
from app.utility.environment import environment
from authlib.integrations.requests_client import OAuth2Session
from coinbase.wallet.client import OAuthClient
from app.utility.TokenService import TokenService
import asyncio
import logging



router = APIRouter(
    prefix="/coin",
    tags=["Coinbase"]
)


oauth_session_coinbase = OAuth2Session(
    client_id=environment.COINBASE_CLIENT_ID,
    client_secret=environment.COINBASE_CLIENT_SECRET,
    redirect_uri=environment.COINBASE_REDIRECT_URI,
    scope=environment.COINBASE_CLIENT_TOKEN_SCOPE,
    )

logger = logging.getLogger()



@router.get("/oauth-redirect-url", summary="Returns URL to Coinbase to initiate oauth")
def login_coinbase(request: Request, db: Session = Depends(get_session)):

    token = request.cookies.get("access_token")
    
    #verify the current user
    user_data = user_helper.get_current_user(token, db)

    #clear previous state entries for this user from the db
    clear_states = coinbase_helper.clear_all_states_for_user(user=user_data, db=db)

    if not clear_states:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="unable to clear past state entries for user"
        )
    

    #don't allow user to link if they already have tokens here
    token_service = TokenService(user_id=user_data.id, db=db)

    coinbase_access_token = token_service.get_access_token(exchange_name="coinbase")

    if coinbase_access_token is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{user_data.username} already has active coinbase tokens"
        )


    coinbase_auth_url, state = oauth_session_coinbase.create_authorization_url(url=environment.COINBASE_OAUTH_URL)

    #store state in the db
    stored_state = coinbase_helper.store_state_in_db(user=user_data, state=state, db=db)
    if stored_state is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to store state"
        )


    #build the response
    content = {"coinbase_url": coinbase_auth_url}
    response = JSONResponse(content=content)
    response.set_cookie(key="state", value=state, httponly=True, secure=False)
    
    return response

@router.get("/callback", summary="Coinbase redirect uri", include_in_schema=False)
def coinbase_callback(request: Request, db: Session = Depends(get_session)):

    state_exception = None

    #retrieve all data from the request
    url_state = request.query_params.get("state")
    cookie_state = request.cookies.get("state")

    if url_state is None or cookie_state is None:
        state_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="state missing from url or cookies",
        )
        return HTMLResponse(content=coinbase_helper.get_callback_status_page(state_exception), status_code=state_exception.status_code)

    if url_state != cookie_state:
        state_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="state mismatch url != cookies",
        )
        return HTMLResponse(content=coinbase_helper.get_callback_status_page(state_exception), status_code=state_exception.status_code)

    
    #retrieve state from db
    stored_oauth = coinbase_helper.get_state_by_state(state=url_state, db=db)

    if stored_oauth is None:
        state_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="state not found in db",
        )
        return HTMLResponse(content=coinbase_helper.get_callback_status_page(state_exception), status_code=state_exception.status_code)


    db_state = stored_oauth.state

    #db state must match response state
    if db_state != url_state:
        state_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="state mismatch url != db",
        )
        return HTMLResponse(content=coinbase_helper.get_callback_status_page(state_exception), status_code=state_exception.status_code)

    #retieve the current user
    access_token = request.cookies.get("access_token")
    user_data = user_helper.get_current_user(token=access_token, db=db)

    #state must match current user
    if stored_oauth.user_id != user_data.id:
        state_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="current user not related to current state",
        )
        return HTMLResponse(content=coinbase_helper.get_callback_status_page(state_exception), status_code=state_exception.status_code)





    #get the coinbase code
    code = request.query_params.get("code")

    if code is None:
        state_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No code from Coinbase found",
        )
        return HTMLResponse(content=coinbase_helper.get_callback_status_page(state_exception), status_code=state_exception.status_code)

    token_service = TokenService(user_id=user_data.id, db=db)

    stored_token_status = token_service.exchange_oauth_code_for_tokens(code=code, exchange_name="coinbase")


    if stored_token_status:
         return HTMLResponse(content=coinbase_helper.get_callback_status_page(state_exception), status_code=status.HTTP_200_OK)
    else:
        state_exception = HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to store coinbase tokens",
            )
        return HTMLResponse(content=coinbase_helper.get_callback_status_page(state_exception), status_code=state_exception.status_code)

@router.get("/linked", summary="Is the current user linked to coinbase?")
def login_coinbase(request: Request, db: Session = Depends(get_session)):

    token = request.cookies.get("access_token")
    
    #verify the current user
    user_data = user_helper.get_current_user(token, db)
    
    token_service = TokenService(user_id=user_data.id, db=db)

    coinbase_access_token = token_service.get_access_token(exchange_name="coinbase")

    if coinbase_access_token is None:
        return {"linked" : False}
    else:
        return {"linked": True}

@router.get("/info", summary="Get current user's coinbase account info")
def coinbase_account(request: Request, db: Session = Depends(get_session)):
    
    token = request.cookies.get("access_token")

    #verify the current user
    user_data = user_helper.get_current_user(token, db)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Token"
        )
    
    token_service = TokenService(user_id=user_data.id, db=db)

    coinbase_access_token = token_service.get_access_token(exchange_name="coinbase")

    print(coinbase_access_token)

    if coinbase_access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No coinbase tokens found"
        )
    

    #establish client
    coinbase_client = OAuthClient(access_token=coinbase_access_token, refresh_token="Our App Handles Refreshing")
    
    return coinbase_client.get_current_user()

@router.get("/accounts", summary="Get current user's coinbase accounts")
def coinbase_account(request: Request, db: Session = Depends(get_session)):
    
    token = request.cookies.get("access_token")

    #verify the current user
    user_data = user_helper.get_current_user(token, db)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Token"
        )
    
    token_service = TokenService(user_id=user_data.id, db=db)

    coinbase_access_token = token_service.get_access_token(exchange_name="coinbase")

    if coinbase_access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No coinbase tokens found"
        )
    

    #establish client
    coinbase_client = OAuthClient(access_token=coinbase_access_token, refresh_token="Our App Handles Refreshing")

    
    
    return coinbase_client.get_accounts()

@router.get("/portfolios", summary="Get current user's coinbase portfolios")
def coinbase_account(request: Request, db: Session = Depends(get_session)):
    
    token = request.cookies.get("access_token")

    #verify the current user
    user_data = user_helper.get_current_user(token, db)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Token"
        )
    
    portfolios = coinbase_helper.get_user_portfolios(user=user_data, db=db)

    if portfolios is None:
        logger.error(f"Unable to get portfolios for {user_data.id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error loading portfolios"
        )

    return portfolios



@router.websocket("/ws/balance")
async def websocket_balance_endpoint(websocket: WebSocket, db: Session = Depends(get_session)):
    await websocket.accept()
    logger.info("WebSocket connected")

    try:
        # Extract token from cookies
        token = websocket.cookies.get("access_token")
        logger.debug(f"Token from query params: {token}")

        if not token:
            await websocket.send_json({"error": "unauthorized: no token found"})
            await websocket.close(code=1008)
            return

        # Authenticate user using the token
        user = user_helper.get_current_user(token, db)
        if not user:
            await websocket.send_json({"error": "unauthorized: invalid token"})
            await websocket.close(code=1008)
            return
        
        token_service = TokenService(user_id=user.id, db=db)

        while True:
            coinbase_access_token = token_service.get_access_token(exchange_name="coinbase")
            # Get the user's balance
            balance = coinbase_helper.get_coinbase_balance(coinbase_access_token, db)
            print(balance)
            if isinstance(balance, dict) and 'error' in balance:
                await websocket.send_json({"error": balance['error']})
            else:
                await websocket.send_json({"balance": balance})
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception("Unexpected error in WebSocket")
        await websocket.close(code=1011)
    finally:
        db.close()
        return

