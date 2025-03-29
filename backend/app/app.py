from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router
import app.models #this ensures that the schema is loaded before initializing the db
from app.services.database import db_shutdown, db_startup
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]

)


async def startup():
    '''Tasks to be done on startup'''

    await db_startup()




async def shutdown():
    '''Tasks to be done on shutdown'''
    #Nothing right now

    await db_shutdown()



app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)

app.include_router(router, prefix=settings.API_STR)


