from fastapi import APIRouter, HTTPException, status, Request, Depends
from app.utility import user_helper, coinbase_helper
from sqlalchemy.orm import Session
from app.database.db_connection import get_session
from fastapi.responses import JSONResponse, HTMLResponse
from app.utility.environment import environment
import requests
import json
from authlib.integrations.requests_client import OAuth2Session



router = APIRouter(
    prefix="/coinbase",
    tags=["Coinbase"]
)


oauth_session_coinbase = OAuth2Session(
    client_id=environment.COINBASE_CLIENT_ID,
    client_secret=environment.COINBASE_CLIENT_SECRET,
    redirect_uri=environment.COINBASE_REDIRECT_URI,
    scope=environment.COINBASE_CLIENT_TOKEN_SCOPE,
    )



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
    stored_oauth = coinbase_helper.get_state_from_db(state=url_state, db=db)

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
    if stored_oauth.username != user_data.username:
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

    
    #exchange code for tokens, returns an OAuth2Token
    coinbase_tokens = oauth_session_coinbase.fetch_token(
        url=environment.COINBASE_TOKEN_URL,
        method="POST",
        grant_type="authorization_code",
        code=code)
    
    if "access_token" in coinbase_tokens and "refresh_token" in coinbase_tokens:
        db_coinbase_tokens = coinbase_helper.store_new_tokens(response=coinbase_tokens, user=user_data, db=db)
        if db_coinbase_tokens is None:
            state_exception = HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to store coinbase tokens",
            )
            return HTMLResponse(content=coinbase_helper.get_callback_status_page(state_exception), status_code=state_exception.status_code)
    else:
        state_exception = HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Coinbase token exchange failed",
        )
        return HTMLResponse(content=coinbase_helper.get_callback_status_page(state_exception), status_code=state_exception.status_code)
  

    return HTMLResponse(content=coinbase_helper.get_callback_status_page(state_exception), status_code=status.HTTP_200_OK)
  


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
    
    coinbase_token_data = coinbase_helper.get_coinbase_tokens(user=user_data, db=db)

    if coinbase_token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No coinbase tokens found"
        )
    
    return coinbase_helper.get_coinbase_user_info(coinbase_token_data, db)


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
    
    coinbase_token_data = coinbase_helper.get_coinbase_tokens(user=user_data, db=db)

    if coinbase_token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No coinbase tokens found"
        )
    
    return coinbase_helper.get_coinbase_user_accounts(coinbase_token_data, db)


