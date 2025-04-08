from fastapi import HTTPException, status
from app.database.models import OAuth_State, User
from typing import Union
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from app.utility.environment import environment
from app.database.models import Exchange_Auth_Token
import json
import requests
from requests import Response
import logging



logger = logging.getLogger()

@staticmethod
def get_state_from_db(state: str, db: Session) -> Union[OAuth_State, None]:
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
def encrypt(data: str) -> bytes:
    cipher_suite = Fernet(environment.COINBASE_TOKEN_ENCRYPTION_KEY)
    return cipher_suite.encrypt(data.encode('utf-8'))

@staticmethod
def decrypt(data: bytes) -> str:
    cipher_suite = Fernet(environment.COINBASE_TOKEN_ENCRYPTION_KEY)
    return cipher_suite.decrypt(data).decode('utf-8')

@staticmethod
def store_new_tokens(response: dict, user: User, db: Session) -> Union[Exchange_Auth_Token, None]:

    #encrypt the tokens
    access_token = response["access_token"]
    refresh_token = response["refresh_token"]
    
    encrypted_access_token = encrypt(access_token)
    encrypted_refresh_token = encrypt(refresh_token)


    #does this user already have tokens

    existing_tokens = db.query(Exchange_Auth_Token).filter(Exchange_Auth_Token.user_id == user.id, Exchange_Auth_Token.exchange_name == "coinbase").first()

    try:
        if existing_tokens:
            #update
            existing_tokens.access_token = encrypted_access_token
            existing_tokens.refresh_token = encrypted_refresh_token
            existing_tokens.scope = response["scope"]
            existing_tokens.expires_in = response["expires_in"]
            db.commit()
            return existing_tokens
        else:
            #new entry
            new_exchange_token = Exchange_Auth_Token(
                user_id = user.id,
                exchange_name = "coinbase",
                access_token = encrypted_access_token,
                refresh_token = encrypted_refresh_token,
                expires_in = response["expires_in"],
                scope = response["scope"]

            )
        
            db.add(new_exchange_token)
            db.commit()
            return new_exchange_token
    
    except SQLAlchemyError as e:
        logger.error(f"DB error trying to add token for {user.username}")
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
def get_coinbase_tokens(user: User, db: Session) -> Union[Exchange_Auth_Token, None]:

    
    result = (db.execute(select(Exchange_Auth_Token).where(Exchange_Auth_Token.user_id == user.id))).scalars().first()

    #TODO check that the access token is still alive, if it is not then get a new one via refresh coinbase access token
    
    return result

@staticmethod
def get_coinbase_user_info(token: Exchange_Auth_Token, db: Session):

    access_token = decrypt((token.access_token))

    url = "https://api.coinbase.com/v2/user"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url=url, headers=headers)

    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return {}


@staticmethod
def get_coinbase_user_accounts(token: Exchange_Auth_Token, db: Session):

    access_token = decrypt((token.access_token))

    url = "https://api.coinbase.com/v2/accounts"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url=url, headers=headers)

    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return {}

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
            






#TODO helper function to get a new access token for the current user
@staticmethod
def refresh_coinbase_access_token(auth: Exchange_Auth_Token, user: User):
    #get a new access token curl https://login.coinbase.com/oauth2/token \
    #   -X POST \
    #   -d 'grant_type=refresh_token&
    #       client_id=YOUR_CLIENT_ID&
    #       client_secret=YOUR_CLIENT_SECRET&
    #       refresh_token=REFRESH_TOKEN'
    # refresh tokens expire after 1.5 years
    # access tokens expire in one hour
    pass