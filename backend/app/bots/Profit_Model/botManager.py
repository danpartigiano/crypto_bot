# app/botManager.py

import os
import json
import logging
from multiprocessing import Process
from importlib import import_module

from sqlalchemy.future import select
from app.database.db_connection import context_get_session
from app.database.models import Bot

# Directory where each bot lives
BOTS_DIRECTORY = os.path.join(os.path.dirname(__file__), "bots")

# Global list of running processes
bot_processes = []

# Configure root logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def load_bot_info(bot_path: str) -> dict | None:
    """
    Read and validate info.json in the bot directory.
    Returns the parsed dict if it contains name, description, asset_types.
    """
    info_file = os.path.join(bot_path, "info.json")
    if not os.path.exists(info_file):
        logger.error(f"{bot_path} missing info.json")
        return None

    with open(info_file, "r") as f:
        data = json.load(f)

    required = {"name", "description", "asset_types"}
    if not required.issubset(data.keys()):
        logger.error(f"{bot_path}/info.json missing one of {required}")
        return None

    return data


def load_bot_into_db(bot_info: dict) -> int | None:
    """
    Insert or update the bot record in the database.
    Returns the bot.id.
    """
    with context_get_session() as db:
        try:
            existing = db.scalars(
                select(Bot).where(Bot.name == bot_info["name"])
            ).first()

            if existing is None:
                new_bot = Bot(
                    name=bot_info["name"],
                    description=bot_info["description"],
                    asset_types=bot_info["asset_types"]
                )
                db.add(new_bot)
                db.commit()
                db.refresh(new_bot)
                return new_bot.id

            # Update description if changed
            if existing.description != bot_info["description"]:
                existing.description = bot_info["description"]
                db.commit()

            return existing.id

        except Exception as e:
            db.rollback()
            logger.error(f"DB error for bot {bot_info['name']}: {e}")
            return None


def startup_all_bots():
    """
    Discover every valid bot folder, register in DB,
    and spawn generator + processor for each.
    """
    logger.info(f"Starting all bots in {BOTS_DIRECTORY}")

    for bot_name in os.listdir(BOTS_DIRECTORY):
        if bot_name == "__pycache__":
            continue

        bot_path = os.path.join(BOTS_DIRECTORY, bot_name)
        if not os.path.isdir(bot_path):
            continue

        info = load_bot_info(bot_path)
        if not info:
            continue

        bot_id = load_bot_into_db(info)
        if bot_id is None:
            logger.error(f"Skipping {bot_name}: no DB id")
            continue

        try:
            gen_mod  = import_module(f"app.bots.{bot_name}.signalGenerator")
            proc_mod = import_module(f"app.bots.{bot_name}.signalProcessor")
        except ImportError as ie:
            logger.error(f"Cannot
