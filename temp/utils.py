import bcrypt
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from typing import Union, Any
from jose import jwt
from sqlalchemy.orm import Session
from models import User


#load the environment variables
load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_MINUTES = 10080
ALGORITHM = os.environ['ALGORITHM']
JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']
JWT_REFRESH_SECRET_KEY = os.environ['JWT_REFRESH_SECRET_KEY']

def get_password_hash(password: str) -> str:
    '''Generates the hash of the given password'''
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt)

def verify_password(password: str, hashed_password: str) -> bool:
    '''Verifies if the given password matches the given hash'''
    password_bytes = password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password)

def authenticate_user(username: str, password: str, db: Session) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password=password, hashed_password=user.hashed_password):
        return None
    return user

def create_access_token(username: str, user_id: int, expires_delta: int = None) -> str:

    if expires_delta is not None:
        expires_delta = datetime.now(timezone.utc) + expires_delta
    else:
        expires_delta = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": username, "id" : user_id}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)
    return encoded_jwt

def create_refresh_token(username: str, user_id: int, expires_delta: int = None) -> str:
    
    if expires_delta is not None:
        expires_delta = datetime.now(timezone.utc) + expires_delta
    else:
        expires_delta = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": username, "id" : user_id}
    encoded_jwt = jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, ALGORITHM)
    return encoded_jwt

def decode_refresh_token(refresh_token: str):

    
    payload = jwt.decode(refresh_token, JWT_REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
    user_id = payload.get("id")
    username = payload.get("sub")

    # JWTError : &nbsp;&nbsp;&nbsp;&nbsp;:empty: If the signature is invalid in any way.
    # ExpiredSignatureError : &nbsp;&nbsp;&nbsp;&nbsp;:empty: If the signature has expired.
    # JWTClaimsError : &nbsp;&nbsp;&nbsp;&nbsp;:empty: If any claim is invalid in any way.
    
    return user_id, username
