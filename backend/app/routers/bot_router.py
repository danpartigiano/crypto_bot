from fastapi import APIRouter, HTTPException, status, Request, Depends
from app.utility import bot_helper, user_helper, coinbase_helper
from sqlalchemy.orm import Session
from app.database.db_connection import get_session
from fastapi.responses import JSONResponse, HTMLResponse
from app.utility.environment import environment
from authlib.integrations.requests_client import OAuth2Session
from coinbase.wallet.client import OAuthClient
from app.utility.TokenService import TokenService
import logging
from app.database.schemas import Subscription



router = APIRouter(
    prefix="/bots",
    tags=["Bots"]
)

logger = logging.getLogger()



@router.get("", summary="Get information on all the currently available bots")
def bots(db: Session = Depends(get_session)):
    return  bot_helper.get_all_bots(db=db)


@router.post("/subscribe", summary="Subscribe to a bot")
def bots(data: Subscription, request: Request, db: Session = Depends(get_session)):
    
    token = request.cookies.get("access_token")

    #verify the current user
    user_data = user_helper.get_current_user(token, db)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Token"
        )
    
    #verify bot_id
    bot = bot_helper.get_bot_by_id(id=data.bot_id, db=db)

    if bot is None:
        logger.error(f"Bot {data.bot_id} not found")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No bot {data.bot_id}"
        )
    
    #verify portfolio_uuid and that the required types are present
    portfolios = coinbase_helper.get_user_portfolios(user = user_data, db=db)

    if portfolios is None:
        logger.error(f"No portfolios for {user_data.id} found")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No portfolios for {user_data.id} found"
        )

    #ensure the portfolio has all the required trading asset types

    required_assets = bot.asset_types.copy()

    for portfolio in portfolios["portfolios"]:
        if portfolio["portfolio"]["uuid"] == data.portfolio_uuid and portfolio["portfolio"]["deleted"] == False:

            #check that this portfolio includes all required asset types

            for position in portfolio["spot_positions"]:
                if position["asset"] in required_assets:
                    required_assets.remove(position["asset"])
            
            if len(required_assets) != 0:
                logger.error(f"User {user_data.id} is missing assets {required_assets}, so they can't subscribe to {bot.id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing assets {required_assets} in portfolio {portfolio["portfolio"]["name"]}. Unable to subscribe to Bot {bot.name}"
                )
            else:
                subscription = bot_helper.subscribe_user_to_bot(user=user_data, bot=bot, portfolio_uuid=data.portfolio_uuid, db=db)

                if subscription is None:
                    logger.error(f"User {user_data.id} can't be subscribed to bot {bot.id}, either already subscribed or db error")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Can't subscribe {user_data.id} to {bot.id}. Either already subscribed or db error"
                    )


            break
    
    
        
    return {"status", "success"}


@router.post("/unsubscribe", summary="Unsubscribe from a bot")
def bots(data: Subscription, request: Request, db: Session = Depends(get_session)):
    
    token = request.cookies.get("access_token")

    #verify the current user
    user_data = user_helper.get_current_user(token, db)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Token"
        )

    return bot_helper.unsubscribe_user_from_bot(user=user_data, portfolio_uuid=data.portfolio_uuid, db=db)

