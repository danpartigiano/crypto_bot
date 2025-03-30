from fastapi import Depends
from app.database.schemas import UserSchema
from app.utility.utils import get_password_hash, verify_password, decrypt_access_token
from app.database.models import User
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Union
from sqlalchemy.future import select
from fastapi import HTTPException, status
import logging

logger = logging.getLogger()

def add_user_to_db(user: UserSchema, db: Session) -> Union[User, None]:
    '''Add the user to the database'''
    
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        username=user.username,
        hashed_password=get_password_hash(user.password)
    )

    # check is this user is already in the db
    existing_username = get_user_by_username(user.username, db)
    if existing_username is not None:
        logger.error(f"A user with username {user.username} already exists")
        return None
    
    existing_email = get_user_by_email(user.email, db)
    if existing_email is not None:
        logger.error(f"A user with email {user.email} already exists")
        return None
    
    
    try:
        db.add(new_user)
        db.commit()
        return new_user
    
    except SQLAlchemyError as e:
        logger.error(f"DB error trying to add {user.username}")
        db.rollback()
        return None

def get_user_by_username(username: str, db: Session) -> Union[User, None]:
    '''Gets the user from the database based on the provided username'''

    result =  db.execute(select(User).where(User.username == username))
    return result.scalars().first()
    
def get_user_by_email(email: str, db: Session) -> Union[User, None]:
    '''Gets the user from the database based on the provided email'''  
    
    result =  db.execute(select(User).where(User.email == email))
    return result.scalars().first()

def authenticate_user(username: str, password: str, db: Session) -> Union[User, None]:
    user = get_user_by_username(username=username, db=db)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def get_current_user(token: str, db: Session) -> User:
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials"
    )

    username = decrypt_access_token(token)

    if username is None:
        raise credentials_exception
    
    user = get_user_by_username(username=username, db=db)

    if user is None:
        raise credentials_exception
    
    return user
    

