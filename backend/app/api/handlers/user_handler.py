from fastapi import APIRouter
from app.schemas.user_schema import User

user_router = APIRouter()

@user_router.post('/create', summary="Create a new user")
async def create_user(data: User):
    return {"msg": "here"}


@user_router.post('/login', summary="Create a new user")
async def create_user():
    return {"msg": "here"}


@user_router.get('/info', summary="Create a new user")
async def create_user():
    return {"msg": "here"}