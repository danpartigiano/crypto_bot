from fastapi import HTTPException
from app.database.models import OAuth_State, User
from typing import Union
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.utility.environment import environment
import logging

import requests
from datetime import datetime, timezone
from app.database.models import Exchange_Auth_Token


logger = logging.getLogger()


@staticmethod
def get_state_by_state(state: str, db: Session) -> Union[OAuth_State, None]:
    result = db.execute(select(OAuth_State).where(OAuth_State.state == state))
    return result.scalars().first()

@staticmethod
def get_state_by_user_id(user_id: str, db: Session) -> Union[OAuth_State, None]:
    result = db.execute(select(OAuth_State).where(OAuth_State.user_id == user_id))
    return result.scalars().first()

@staticmethod
def store_state_in_db(user: User, state: str, db: Session) -> Union[OAuth_State, None]:

    #link the state to the current user in the database
    new_oauth_state = OAuth_State(state=state, user_id=user.id)

    try:
        db.add(new_oauth_state)
        db.commit()
        return new_oauth_state

    except SQLAlchemyError as e:
        db.rollback()
        return None

@staticmethod
def remove_state(state: OAuth_State, db: Session) -> Union[OAuth_State, None]:
    try:
        db.delete(state)
        db.commit()
        return state
    
    except SQLAlchemyError as e:
        logger.error(f"Error deleting state for {state.user_id}")
        db.rollback()
        return None
    
@staticmethod
def clear_all_states_for_user(user: User, db: Session) -> bool:
    try:
        db.query(OAuth_State).filter(OAuth_State.user_id == user.id).delete(synchronize_session=False)
        db.commit()
        return True
    
    except SQLAlchemyError as e:
        logger.error(f"Error deleting state for {user.username}")
        db.rollback()
        return False
    
@staticmethod
def get_callback_status_page(error_message: HTTPException | None):
    "Returns an html page used to show if the client's coinbase oauth exchange was successful"

    circle_color = "green"
    message = "Coinbase Account Linked to Crypto Bot!"
    symbol = "&#x2714"

    if error_message is not None:
        #there was an error
        circle_color = "red"
        message = f"HTTP ERROR {error_message.status_code}: {error_message.detail}"
        symbol = "&#10060"


    webpage = f"""
        <html>
            <head><title>Coinbase OAuth Status</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: black;">
                <div style="margin-bottom: 20px;">
                    <div style="background-color: {circle_color}; color: white; 
                                width: 150px; height: 150px; 
                                border-radius: 50%; display: flex; justify-content: center; align-items: center; 
                                font-size: 100px; margin: 0 auto;">
                        {symbol}
                    </div>
                </div>
                <h2 style="color: white;">{message}</h2>
                <br>
            </body>
        </html>
        """

    return webpage

def refresh_coinbase_token(token_obj: Exchange_Auth_Token, db: Session) -> bool:
    try:
        refresh_token = token_obj.refresh_token.decode()
        client_id = environment.get("COINBASE_CLIENT_ID")
        client_secret = environment.get("COINBASE_CLIENT_SECRET")

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        response = requests.post("https://api.coinbase.com/oauth/token", data=payload)

        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.text}")
            token_obj.refresh_attempts += 1
            db.commit()
            return False

        tokens = response.json()

        token_obj.access_token = tokens["access_token"].encode()
        token_obj.refresh_token = tokens["refresh_token"].encode()
        token_obj.expires_at = int(datetime.now(timezone.utc).timestamp()) + tokens["expires_in"]
        token_obj.refresh_attempts = 0
        db.commit()

        return True

    except Exception as e:
        logger.exception("Exception during token refresh")
        db.rollback()
        return False

def get_coinbase_balance(user: User, db: Session):
    token_obj = user.exchange_tokens
    
    if not token_obj:
        return {"error": "No Coinbase token found"}

    if token_obj.is_expired():
        refreshed = refresh_coinbase_token(token_obj, db)
        if not refreshed:
            return {"error": "Token refresh failed"}
    
    access_token = token_obj.access_token.decode()
    
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "CB-VERSION": "2021-10-01"
    }

    response = requests.get("https://api.coinbase.com/v2/accounts", headers=headers)

    if response.status_code != 200:
        return {"error": f"Coinbase API failed: {response.status_code}"}

    balances = {}
    for account in response.json().get("data", []):
        balances[account["currency"]] = account["balance"]["amount"]

    return balances


