from fastapi import APIRouter, HTTPException, status, Request, Depends, Form
from fastapi.responses import JSONResponse
from app.database.schemas import UserSchema
from app.utility import user_helper, bot_helper
from app.utility.utils import create_access_token
from sqlalchemy.orm import Session
from app.database.db_connection import get_session
import logging



router = APIRouter(
    prefix="/user",
    tags=["User"]
)

logger = logging.getLogger()


@router.post('/create', summary="Create a new user")
def user_create(data: UserSchema, db: Session = Depends(get_session)):

    new_user = user_helper.add_user_to_db(data, db)

    if new_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to add new user"
        )
    
    #login the new user
    return user_login(username=data.username, password=data.password, db=db)

@router.post('/login', summary="Login a user")
def user_login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_session)):

    #TODO username and password are sent in plaintext in the url
    #TODO what if an access token is sent and is still valid?

    user = user_helper.authenticate_user(username, password, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token=create_access_token(user.username)

    content = {"status" : "success"}
    response = JSONResponse(content=content)
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False)

    return response

@router.post('/logout', summary="Invalidate the current access token")
def user_logout(request: Request, db: Session = Depends(get_session)):
    # Get token from the request cookie.
    access_token = request.cookies.get("access_token")
    
    # If no token exists, clear cookie and return success.
    if not access_token:
        response = JSONResponse(content={"status": "success", "detail": "No active session"})
        response.delete_cookie("access_token")
        return response

    # Validate token; even if invalid, we'll clear it.
    user = user_helper.get_current_user(access_token, db)
    # You may log or handle the case of an invalid token if needed.
    response = JSONResponse(content={"status": "success"})
    response.delete_cookie("access_token")
    return response

@router.get('/info', summary="Get currently logged in user information")
def user_info(request: Request, db: Session = Depends(get_session)):

    #get token from request
    access_token = request.cookies.get("access_token")

    user = user_helper.get_current_user(access_token, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )
    
    user.hashed_password = None

    return user

@router.get('/refresh-token', summary="Refresh a current access token")
def refresh_token(request: Request, db: Session = Depends(get_session)):


    access_token = request.cookies.get("access_token")

    user = user_helper.get_current_user(access_token, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )
    
    access_token=create_access_token(user.username)

    content = {"status" : "success"}
    response = JSONResponse(content=content)
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False)

    return response


@router.get("/subscriptions", summary="Get this user's subscriptions")
def bots(request: Request, db: Session = Depends(get_session)):

    #get token from request
    access_token = request.cookies.get("access_token")

    user = user_helper.get_current_user(access_token, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )




    return  bot_helper.get_subscriptions_for_user(user=user, db=db)