import os
import json
import logging
from multiprocessing import Process
from importlib import import_module

from sqlalchemy.future import select
from app.database.db_connection import context_get_session
from app.database.models            import Bot

BOTS_DIRECTORY = os.path.join(os.path.dirname(__file__), "bots")
bot_processes = []

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def load_bot_info(bot_path: str) -> dict | None:
    info_file = os.path.join(bot_path, "info.json")
    if not os.path.exists(info_file):
        return None
    with open(info_file) as f:
        data = json.load(f)
    if not {"name","description","asset_types"}.issubset(data):
        return None
    return data

def load_bot_into_db(bot_info: dict) -> int | None:
    with context_get_session() as db:
        existing = db.scalars(
            select(Bot).where(Bot.name==bot_info["name"])
        ).first()
        if existing is None:
            new = Bot(**bot_info)
            db.add(new); db.commit(); db.refresh(new)
            return new.id
        if existing.description != bot_info["description"]:
            existing.description = bot_info["description"]
            db.commit()
        return existing.id

def startup_all_bots():
    logger.info(f"Starting bots from {BOTS_DIRECTORY}")
    for name in os.listdir(BOTS_DIRECTORY):
        if name=="__pycache__": continue
        path = os.path.join(BOTS_DIRECTORY, name)
        if not os.path.isdir(path): continue

        info = load_bot_info(path)
        if not info: continue

        bot_id = load_bot_into_db(info)
        if bot_id is None: continue

        try:
            gen = import_module(f"app.bots.{name}.signalGenerator").main
            proc= import_module(f"app.bots.{name}.signalProcessor").main
        except ImportError as e:
            logger.error(f"Import failed for {name}: {e}")
            continue

        logger.info(f"Launching {name} (ID={bot_id})")
        p1 = Process(target=gen,  args=(bot_id,), name=f"{name}-Gen")
        p2 = Process(target=proc, args=(bot_id,), name=f"{name}-Proc")
        p1.start(); p2.start()
        bot_processes.extend([p1,p2])

    logger.info("All bots launched.")

def shutdown_all_bots():
    logger.info("Shutting down bots…")
    for p in bot_processes:
        if p.is_alive():
            p.terminate()
            p.join()
            logger.info(f"Terminated {p.name}")

if __name__=="__main__":
    startup_all_bots()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        shutdown_all_bots()
