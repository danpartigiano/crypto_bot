from multiprocessing import Process
import logging
import json
import os
from importlib import import_module
from app.database.db_connection import context_get_session
from app.database.models import Bot
from sqlalchemy.future import select
import time
from app.utility.environment import environment


#not using multithreading because of the global interpreter lock of python -> only one thread can execute python byte code at a time
#   this would mean signal generation would wait on trade execution or trade execution would wait on signal generation (both are bad)

# Logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


bot_processes: list[Process] = []

BOTS_DIRECTORY = os.path.join(os.path.dirname(__file__))



def load_bot_info(bot_path):

    file = os.path.join(bot_path, "info.json")

    if os.path.exists(file):
        with open(file, "r") as file:
            bot_data = json.load(file)
            #ensure bot info 
            expected_info = {"name", "description", "asset_types"}
            if all(key in bot_data for key in expected_info):
                return bot_data
            else:
                logger.error(f"{bot_path} does not contain a complete info.json")
                return None
        
    logger.error(f"{bot_path} does not contain info.json")
    return None

def startup_all_bots():
    global bot_processes

    logger.info(f"Starting all bots in: {BOTS_DIRECTORY}")

    for bot_name in os.listdir(BOTS_DIRECTORY):

        #skip __pycache__
        if bot_name == "__pycache__":
            continue

        bot_path = os.path.join(BOTS_DIRECTORY, bot_name)

        if not os.path.isdir(bot_path):
            logger.info(f"{bot_path} is not a bot folder")
            continue

        # Get data for this bot
        bot_info = load_bot_info(bot_path)

        if not bot_info:
            logger.error(f"Unable to start bot at {bot_path}")
            continue

        logger.info(f"Starting bot at {bot_name}")

        # Get signal generator and processor for this bot
        signal_generator_path = os.path.join(bot_path, "signalGenerator.py")
        signal_processor_path = os.path.join(bot_path, "signalProcessor.py")

        if not os.path.exists(signal_generator_path) or not os.path.exists(signal_processor_path):
            logger.error(f"{bot_name} does not have accompaning generator and/or processor")
            continue

        #get modules for bot
        signal_generator = import_module(f"app.bots.{bot_name}.signalGenerator").main
        signal_processor = import_module(f"app.bots.{bot_name}.signalProcessor").main

        #load bot info into db if need be, otherwise get id from db
        bot_id = load_bot_into_db(bot_info)

        if bot_id is None:
            logger.error("Can't start a bot without an id")
            continue

        process1 = Process(target=signal_generator, args=(bot_id,), name=f"{bot_name}:{bot_id}:Generator")
        process2 = Process(target=signal_processor, args=(bot_id,), name=f"{bot_name}:{bot_id}:Processor")
        
        process1.start()
        process2.start()

        bot_processes.append(process1)
        bot_processes.append(process2)

        logger.info(f"{bot_name} started")

def load_bot_into_db(bot_info: dict):
    
     with context_get_session() as db:

        
        try:
            #is this bot already in the db
            bot = db.scalars(select(Bot).where(Bot.name == bot_info["name"])).first()

            if bot is None:
                #new bot, add it to the db
                new_bot = Bot(
                    name=bot_info["name"],
                    description=bot_info["description"],
                    asset_types=bot_info["asset_types"]
                )
                db.add(new_bot)
                db.commit()
                db.refresh(new_bot)
                return new_bot.id
            else:
                #check if the description has changed, if it has then change it
                if bot.description != bot_info["description"]:
                    bot.description = bot_info["description"]
                    db.commit()
                return bot.id
        except Exception as e:
            db.rollback()
            logger.error(f"Unable to add/update {bot_info['name']} in db: {e}")
            return None

def shutdown_all_bots():

    global bot_processes

    for process in bot_processes:
        if process and process.is_alive():
            process.terminate()
            process.join()
            logger.info(f"{process.name} has been shutdown")

def check_bots():
    """Ensures all bot processes are running"""
    global bot_processes

    while environment.BOT_MONITOR:

        for i, bot_process in enumerate(bot_processes):

            if not bot_process.is_alive():
                #bot is not alive, attempt restart once
                logger.info(f"{bot_process.name} is dead, attempting restart")

                bot_identity = bot_process.name.split(":")

                bot_name = bot_identity[0]
                bot_id = bot_identity[1]
                bot_type = bot_identity[2]

                bot_path = os.path.join(BOTS_DIRECTORY, bot_name)
                
                if bot_type == "Generator":

                    signal_generator = import_module(f"app.bots.{bot_name}.signalGenerator").main

                    new_process = Process(target=signal_generator, args=(bot_id,), name=f"{bot_name}:{bot_id}:Generator")

                    new_process.start()

                    bot_processes[i] = new_process


                else:

                    signal_processor = import_module(f"app.bots.{bot_name}.signalProcessor").main

                    new_process = Process(target=signal_processor, args=(bot_id,), name=f"{bot_name}:{bot_id}:Processor")

                    new_process.start()

                    bot_processes[i] = new_process


                    

                logger.info(f"{bot_process.name} restarted")

            else:
                logger.info(f"{bot_process.name} is alive")
        
        time.sleep(60)
        
    logger.info("Bot monitoring stopped")      