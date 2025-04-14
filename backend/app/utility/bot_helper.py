from fastapi import HTTPException
from app.database.models import Bot
from typing import Union, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.utility.environment import environment
import logging


logger = logging.getLogger()


def get_all_bots(db: Session) -> List[Bot]:

    bots = db.scalars(select(Bot)).all()
    return bots


def get_bot_by_id(id: int, db: Session) -> Union[Bot, None]:
    bot = db.execute(select(Bot).where(Bot.id == id))
    return bot

def get_bot_by_name(name: str, db: Session) -> Union[Bot, None]:
    bot = db.execute(select(Bot).where(Bot.name == name))
    return bot