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
import json
from requests import Response
import logging



logger = logging.getLogger()



def generate_state() -> str:
    return secrets.token_urlsafe(16) #TODO make sure this has a TTL in DB

def get_oauth_from_state(state: str, db: Session) -> Union[OAuth_State, None]:
    result = db.execute(select(OAuth_State).where(OAuth_State.state == state))
    return result.scalars().first()

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
    
def encrypt(data: str) -> bytes:
    cipher_suite = Fernet(environment.COINBASE_TOKEN_ENCRYPTION_KEY)
    return cipher_suite.encrypt(data)

def decrypt(data: bytes) -> str:
    cipher_suite = Fernet(environment.COINBASE_TOKEN_ENCRYPTION_KEY)
    return cipher_suite.decrypt(data).decode()

def store_new_tokens(response: Response, user: User, db: Session) -> Union[Exchange_Auth_Token, None]:

    response_dict = json.loads(response.text)

    
    #encrypt the tokens
    access_token = response_dict["acess_token"]
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

def remove_state(state: OAuth_State, db: Session) -> Union[OAuth_State, None]:
    try:
        db.delete(state)
        db.commit()
        return state
    
    except SQLAlchemyError as e:
        logger.error(f"Error deleting state for {state.username}")
        db.rollback()
        return None
