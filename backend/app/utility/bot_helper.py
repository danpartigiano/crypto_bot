from fastapi import HTTPException
from app.database.models import Bot, User, Subscription
from typing import Union, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.utility.environment import environment
import logging


logger = logging.getLogger()

@staticmethod
def get_all_bots(db: Session) -> List[Bot]:

    bots = db.scalars(select(Bot)).all()
    return bots

@staticmethod
def get_bot_by_id(id: int, db: Session) -> Union[Bot, None]:
    bot = db.scalars(select(Bot).where(Bot.id == id)).first()
    return bot

@staticmethod
def get_bot_by_name(name: str, db: Session) -> Union[Bot, None]:
    bot = db.scalars(select(Bot).where(Bot.name == name)).first()
    return bot

@staticmethod
def get_subscription_by_portfolio_uuid(portfolio_uuid: str, db: Session) -> Union[Subscription, None]:
    subscription = db.scalars(select(Subscription).where(Subscription.portfolio_uuid == portfolio_uuid)).first()
    return subscription

@staticmethod
def subscribe_user_to_bot(user: User, bot: Bot, portfolio_uuid: str, db: Session) -> Union[Subscription, None]:


    #check if this portfolio is already subscribed to a bot
    active_subscription = get_subscription_by_portfolio_uuid(portfolio_uuid=portfolio_uuid, db=db)

    if active_subscription is not None:
        return None

    new_subscription = Subscription(
        bot_id=bot.id,
        user_id=user.id,
        portfolio_uuid=portfolio_uuid

        
    )
    
    try:
        db.add(new_subscription)
        db.commit()
        db.refresh(new_subscription)
        return new_subscription
    
    except SQLAlchemyError as e:
        logger.error(f"DB error trying to subscribe {user.id} portfolio {portfolio_uuid} to bot {bot.id}")
        db.rollback()
        return None
    
@staticmethod
def unsubscribe_user_from_bot(user: User, portfolio_uuid: str, db: Session) -> Union[Subscription, None]:


    #check that the user is subscribed to this bot
    active_subscription = get_subscription_by_portfolio_uuid(portfolio_uuid=portfolio_uuid, db=db)

    if active_subscription is None:
        return {"status": "not found" , "msg": f"User is not subscribed to that bot"}
    
    try:
        db.delete(active_subscription)
        db.commit()
        return {"status": "success"}
    
    except SQLAlchemyError as e:
        logger.error(f"DB error trying to subscribe {user.id} portfolio {portfolio_uuid} to bot {bot.id}")
        db.rollback()
        return None
    
@staticmethod
def get_subscriptions_for_user(user: User, db: Session):
    subscriptions = db.scalars(select(Subscription).where(Subscription.user_id == user.id)).all()
    return subscriptions
    
