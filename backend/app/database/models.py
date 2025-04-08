from sqlalchemy import Column, Integer, String, LargeBinary, Boolean, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from datetime import datetime, timezone

class User(Base):
    '''Relation for the users of our platform'''
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(LargeBinary)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    active = Column(Boolean, default=True)

    exchange_tokens = relationship("Exchange_Auth_Token", back_populates="user", uselist=False)

    subscriptions = relationship("Subscription", back_populates="user")

    def __str__(self) -> str:
        return self.username


class OAuth_State(Base):
    '''Relation to hold state during Coinbase OAuth'''
    __tablename__ = "oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", backref="oauth_states")


class Exchange_Auth_Token(Base):
    '''Relation to hold access tokens to exchanges'''
    __tablename__ = "exchange_auth_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    exchange_name = Column(String, index=True)
    access_token = Column(LargeBinary)
    refresh_token = Column(LargeBinary)
    expires_in = Column(Integer)
    created_at = Column(TIMESTAMP, default=lambda: datetime.now(timezone.utc))
    scope = Column(String, nullable=True)

    user = relationship("User", back_populates="exchange_tokens")
    subscription = relationship("Subscription", back_populates="token")

    __table_args__ = (
        UniqueConstraint("user_id", "exchange_name", name="_exchange_user_unique_constriant"),
    )


class Bot(Base):
    '''Relation to hold bot information'''
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, default="")

    subscriptions = relationship("Subscription", back_populates="bot")


class Subscription(Base):
    '''Relation to hold user subscriptions to bots'''
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    token_id = Column(Integer, ForeignKey("exchange_auth_tokens.id"), index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), index=True)

    
    user = relationship("User", back_populates="subscriptions")
    bot = relationship("Bot", back_populates="subscriptions")
    token = relationship("Exchange_Auth_Token", back_populates="subscription")

