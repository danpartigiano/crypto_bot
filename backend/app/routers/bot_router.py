from fastapi import APIRouter, HTTPException, status, Request, Depends
from app.utility import bot_helper, user_helper
from sqlalchemy.orm import Session
from app.database.db_connection import get_session
from fastapi.responses import JSONResponse, HTMLResponse
from app.utility.environment import environment
from authlib.integrations.requests_client import OAuth2Session
from coinbase.wallet.client import OAuthClient
from app.utility.TokenService import TokenService



router = APIRouter(
    prefix="/bots",
    tags=["Bots"]
)



@router.get("", summary="Get information on all the currently available bots")
def bots(db: Session = Depends(get_session)):
    return  bot_helper.get_all_bots(db=db)


@router.post("/subscribe", summary="Subscribe to a bot")
def bots(request: Request, db: Session = Depends(get_session)):
    
    token = request.cookies.get("access_token")

    #verify the current user
    user_data = user_helper.get_current_user(token, db)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Token"
        )
    
    #TODO logic to process subscription


    #ensure the account type matches the bot type


    #do they have an account in the cryptocurrency the bot is trading?

    
    return 




@router.post("/unsubscribe", summary="Unsubscribe from a bot")
def bots(request: Request, db: Session = Depends(get_session)):
    
    token = request.cookies.get("access_token")

    #verify the current user
    user_data = user_helper.get_current_user(token, db)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Token"
        )
    
    #TODO logic to process unsubscription

    
    return 

