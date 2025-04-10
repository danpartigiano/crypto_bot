import bcrypt
from fastapi import APIRouter, HTTPException, status, Request, Depends
from datetime import datetime, timedelta, timezone
from typing import Union
from datetime import datetime, timezone, timedelta
from app.utility.environment import environment
from jose import jwt, ExpiredSignatureError, JWTError

def get_password_hash(password: str) -> str:
    '''Generates the hash of the given password'''
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt)

def verify_password(password: str, hashed_password: str) -> bool:
    '''Verifies if the given password matches the given hash'''
    password_bytes = password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password)

def create_access_token(username: str, expires_delta: timedelta | None = None) -> str:

    if expires_delta is not None:
        expires_delta = datetime.now(timezone.utc) + expires_delta
    else:
        expires_delta = datetime.now(timezone.utc) + timedelta(minutes=environment.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": username}
    encoded_jwt = jwt.encode(to_encode, environment.JWT_SECRET_KEY, environment.ALGORITHM)
    return encoded_jwt

def decrypt_access_token(token: str) -> Union[str, None]:
    try:
        payload = jwt.decode(
            token,
            environment.JWT_SECRET_KEY,
            algorithms=[environment.ALGORITHM]
        )
        return payload.get("sub")  # or whatever claim you're storing
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    

def create_refresh_token(username: str, expires_delta: timedelta | None = None) -> str:
    if expires_delta is None:
        expires_delta = datetime.utcnow() + timedelta(days=7)
    else:
        expires_delta = datetime.utcnow() + expires_delta

    to_encode = {"exp": expires_delta, "sub": username}
    return jwt.encode(to_encode, environment.JWT_SECRET_KEY, algorithm=environment.ALGORITHM)
