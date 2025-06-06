from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.utility.environment import environment
from app.database.db_connection import engine, Base
import app.database.models #this ensures that the schema is loaded before initializing the db
from app.routers import user_router, coinbase_router, bot_router
import logging, coloredlogs
from app.bots import botManager
import threading
import os


# Logging
coloredlogs.install()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

#Frontend request
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def startup():
    '''Tasks to be done on startup'''

    if not environment.PRODUCTION:
        Base.metadata.drop_all(bind=engine)  #Only for development purposes
    Base.metadata.create_all(bind=engine)

    botManager.startup_all_bots()


    bot_check_thread = threading.Thread(target=botManager.check_bots, daemon=True)
    bot_check_thread.start()


def shutdown():
    '''Tasks to be done on shutdown'''

    #signal bot monitor thread to stop
    os.environ["BOT_MONITOR"] = "False"


    botManager.shutdown_all_bots()

    engine.dispose()

app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)


app.include_router(user_router.router)
app.include_router(coinbase_router.router)
app.include_router(bot_router.router)

#used for testing
@app.get("/")
def root():
    return {"msg": "the app is running"}
