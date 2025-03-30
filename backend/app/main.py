from fastapi import FastAPI
from app.utility.environment import environment
from app.database.db_connection import engine, Base
import app.database.models #this ensures that the schema is loaded before initializing the db
from app.routers import user_router, coinbase_router
import logging


# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

def startup():
    '''Tasks to be done on startup'''

    if not environment.PRODUCTION:
        Base.metadata.drop_all(bind=engine)  #Only for development purposes
    Base.metadata.create_all(bind=engine)


def shutdown():
    '''Tasks to be done on shutdown'''

    engine.dispose()

app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)


app.include_router(user_router.router)
app.include_router(coinbase_router.router)

#used for testing
@app.get("/")
def root():
    return {"msg": "the app is running"}
