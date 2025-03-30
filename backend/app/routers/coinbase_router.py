from fastapi import APIRouter, HTTPException, status, Request, Depends
from app.utility.user_helper import get_current_user, get_user_by_username
from app.utility.coinbase_helper import store_state_in_db, get_oauth_from_state, store_new_tokens, remove_state
from sqlalchemy.orm import Session
from app.database.db_connection import get_session
from fastapi.responses import JSONResponse
from app.utility.environment import environment
import requests
from fastapi.responses import RedirectResponse
# from app.database.models import Exchange_Auth_Token, OAuth_State
import json



router = APIRouter(
    prefix="/coinbase",
    tags=["Coinbase"]
)




@router.get("/oauth-redirect-url", summary="Returns URL to Coinbase to initiate oauth")
def login_coinbase(request: Request, db: Session = Depends(get_session)):

    token = request.cookies.get("access_token")
    
    #verify the current user
    user_data = get_current_user(token, db)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Token"
        )
    
    stored_state = store_state_in_db(user_data, db)

    #construct the url
    coinbase_auth_url = f"{environment.COINBASE_OAUTH_URL}?client_id={environment.COINBASE_CLIENT_ID}&redirect_uri={environment.COINBASE_REDIRECT_URI}&response_type=code&scope={environment.COINBASE_CLIENT_TOKEN_SCOPE}&state={stored_state.state}"


    #build the response
    content = {"coinbase_url": coinbase_auth_url}
    response = JSONResponse(content=content)
    response.set_cookie(key="state", value=stored_state.state, httponly=True, secure=True)
    
    return response

@router.get("/callback", summary="Coinbase redirect uri")
def login_coinbase(request: Request, db: Session = Depends(get_session)):

    state_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate state",
    )

    #retrieve all data from the request
    # state_cookie = request.cookies.get("state")
    state_url = request.query_params.get("state")

    # if state_cookie is None or state_url is None or state_url != state_cookie:
    #     raise state_exception

    if state_url is None:
        raise state_exception
    
    oauth = get_oauth_from_state(db, state_url)

    if oauth is None:
        raise state_exception

    state_db = oauth.state

    user_data = get_user_by_username(username=oauth.username, db=db)

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
    
    new_exchange_auth = store_new_tokens(response, db)

    if new_exchange_auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to store coinbase tokens",
        )
    
    old_state = remove_state(oauth, db)

    if old_state is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to store coinbase tokens - state",
        )    

    #TODO redirect to the frontend
    return RedirectResponse("www.google.com")


#TODO add route for getting current account balance


# link to coinbase scopes https://docs.cdp.coinbase.com/coinbase-app/docs/permissions-scopes


#TODO
#get a new access token curl https://login.coinbase.com/oauth2/token \
#   -X POST \
#   -d 'grant_type=refresh_token&
#       client_id=YOUR_CLIENT_ID&
#       client_secret=YOUR_CLIENT_SECRET&
#       refresh_token=REFRESH_TOKEN'
# refresh tokens expire after 1.5 years
# access tokens expire in one hour
