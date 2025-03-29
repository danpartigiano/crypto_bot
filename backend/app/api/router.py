from fastapi import APIRouter
from app.api.handlers import user_handler

router = APIRouter()


router.include_router(user_handler.user_router, prefix="/user", tags=["User"])
