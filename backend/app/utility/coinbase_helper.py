from fastapi import HTTPException, status
from app.database.models import OAuth_State, User
from typing import Union
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
import secrets
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from app.utility.environment import environment
from app.database.models import Exchange_Auth_Token
from app.database.schemas import CoinbaseToken
import json
import requests
from requests import Response
import logging



logger = logging.getLogger()


@staticmethod
def generate_state() -> str:
    return secrets.token_urlsafe(16) #TODO make sure this has a TTL in DB

@staticmethod
def get_oauth_from_state(state: str, db: Session) -> Union[OAuth_State, None]:
    result = db.execute(select(OAuth_State).where(OAuth_State.state == state))
    return result.scalars().first()

@staticmethod
def get_state_by_username(username: str, db: Session) -> Union[OAuth_State, None]:
    result = db.execute(select(OAuth_State).where(OAuth_State.username == username))
    return result.scalars().first()

@staticmethod
def store_state_in_db(user: User, db: Session) -> Union[OAuth_State, None]:

    #link the state to the current user in the database
    new_oauth_state = OAuth_State(state=generate_state(), username=user.username)

    try:
        db.add(new_oauth_state)
        db.commit()
        return new_oauth_state

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to store state"
        )

@staticmethod    
def encrypt(data: str) -> bytes:
    cipher_suite = Fernet(environment.COINBASE_TOKEN_ENCRYPTION_KEY)
    return cipher_suite.encrypt(data.encode('utf-8'))

@staticmethod
def decrypt(data: bytes) -> str:
    cipher_suite = Fernet(environment.COINBASE_TOKEN_ENCRYPTION_KEY)
    return cipher_suite.decrypt(data).decode('utf-8')

@staticmethod
def store_new_tokens(response: Response, user: User, db: Session) -> Union[Exchange_Auth_Token, None]:

    response_dict = json.loads(response.text)

    
    #encrypt the tokens
    access_token = response_dict["access_token"]
    refresh_token = response_dict["refresh_token"]
    

    encrypted_access_token = encrypt(access_token)
    encrypted_refresh_token = encrypt(refresh_token)

    #TODO validate that scopes match environment

    new_exchange_token = Exchange_Auth_Token(
        user_id = user.id,
        exchange_name = "coinbase",
        access_token = encrypted_access_token,
        refresh_token = encrypted_refresh_token,
        expires_in = response_dict["expires_in"],
        scope = response_dict["scope"]

    )
    try:
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
        logger.error(f"Error deleting state for {state.username}")
        db.rollback()
        return None

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