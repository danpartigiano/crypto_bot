from sqlalchemy import Column, Integer, String, LargeBinary, Boolean, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from datetime import datetime, timezone
from hashlib import blake2b
from sqlalchemy.dialects.postgresql import ARRAY

class User(Base):
    '''Relation for the users of our platform'''
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(LargeBinary)
    created_at = Column(Integer, default=lambda: int(datetime.now(timezone.utc).timestamp()))
    updated_at = Column(Integer, default=lambda: int(datetime.now(timezone.utc).timestamp()), onupdate=lambda: int(datetime.now(timezone.utc).timestamp()))
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
    expires_at = Column(Integer, nullable=False)
    created_at = Column(Integer, default=lambda: int(datetime.now(timezone.utc).timestamp()))
    scope = Column(String, nullable=True)
    refresh_attempts = Column(Integer, default=0, index = True)

    user = relationship("User", back_populates="exchange_tokens")

    __table_args__ = (
        UniqueConstraint("user_id", "exchange_name", name="_exchange_user_unique_constriant"),
    )

    def is_expired(self):
        #what is buffer seconds
        current_time = int(datetime.now(timezone.utc).timestamp())
        return self.expires_at <= current_time + 120 #because UNIX timestamps count up, 2 min buffer
    

    def get_lock_id(self) -> int:
        """Returns 64 bit id of postgres advisory lock for this token"""
        data = f"{self.id}:{self.exchange_name}:{self.user_id}"
        hash_gen = blake2b(digest_size=8)
        hash_gen.update(data.encode())
        return int.from_bytes(hash_gen.digest(), byteorder="big", signed=False)


class Bot(Base):
    '''Relation to hold bot information'''
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, default="")
    asset_types = Column(ARRAY(String), nullable=False)

    subscriptions = relationship("Subscription", back_populates="bot")


class Subscription(Base):
    '''Relation to hold user subscriptions to bots'''
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), index=True)
    portfolio_uuid = Column(String, unique=True, index=True)

    
    user = relationship("User", back_populates="subscriptions")
    bot = relationship("Bot", back_populates="subscriptions")

