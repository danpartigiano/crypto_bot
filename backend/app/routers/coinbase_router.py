from fastapi import APIRouter, HTTPException, status, Request, Depends
from app.utility import user_helper, coinbase_helper
from sqlalchemy.orm import Session
from app.database.db_connection import get_session
from fastapi.responses import JSONResponse
from app.utility.environment import environment
import requests
import json



router = APIRouter(
    prefix="/coinbase",
    tags=["Coinbase"]
)




@router.get("/oauth-redirect-url", summary="Returns URL to Coinbase to initiate oauth")
def login_coinbase(request: Request, db: Session = Depends(get_session)):

    token = request.cookies.get("access_token")
    
    #verify the current user
    user_data = user_helper.get_current_user(token, db)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Token"
        )
    
    #check that user doesn't already have unfinished oauth
     #TODO check is there is already a state in the db (user might started oauth and not finished)
    #TODO delete current state entry is there is one

    stored_state = coinbase_helper.get_state_by_username(user_data.username, db)

    if stored_state is None:
        stored_state = coinbase_helper.store_state_in_db(user_data, db)

    #construct the url
    coinbase_auth_url = f"{environment.COINBASE_OAUTH_URL}?client_id={environment.COINBASE_CLIENT_ID}&redirect_uri={environment.COINBASE_REDIRECT_URI}&response_type=code&scope={environment.COINBASE_CLIENT_TOKEN_SCOPE}&state={stored_state.state}"


    #build the response
    content = {"coinbase_url": coinbase_auth_url}
    response = JSONResponse(content=content)
    response.set_cookie(key="state", value=stored_state.state, httponly=True, secure=True)
    
    return response

@router.get("/callback", summary="Coinbase redirect uri", include_in_schema=False)
def coinbase_callback(request: Request, db: Session = Depends(get_session)):

    state_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate state",
    )

    #retrieve all data from the request
    state_url = request.query_params.get("state")

    if state_url is None:
        raise state_exception
    
    oauth_state = coinbase_helper.get_oauth_from_state(state=state_url, db=db)

    if oauth_state is None:
        raise state_exception

    state_db = oauth_state.state

    if state_db != state_url:
        raise state_exception

    user_data = user_helper.get_user_by_username(username=oauth_state.username, db=db)

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
        "redirect_uri": environment.COINBASE_REDIRECT_URI,
        "client_id": environment.COINBASE_CLIENT_ID,
        "client_secret": environment.COINBASE_CLIENT_SECRET
    }

    response = requests.post(environment.COINBASE_TOKEN_URL, data=content)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to get access tokens from coinbase",
        )
    
    new_exchange_auth = coinbase_helper.store_new_tokens(response=response, user=user_data, db=db)

    if new_exchange_auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to store coinbase tokens",
        )
    
    old_state = coinbase_helper.remove_state(oauth_state, db)

    if old_state is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to store coinbase tokens - state",
        )    

    #TODO redirect to the frontend
    return {"status": "success"}


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


