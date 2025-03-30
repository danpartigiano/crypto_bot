from sqlalchemy import Column, Integer, String, LargeBinary, Boolean, TIMESTAMP, ForeignKey
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

    def __str__(self) -> str:
        return self.username


class OAuth_State(Base):
    '''Relation to hold state during Coinbase OAuth'''

    __tablename__ = "oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String, unique=True, index=True)
    username = Column(String, ForeignKey("users.username"))


class Exchange_Auth_Token(Base):
    '''Relations to hold access tokens to exchanges'''

    __tablename__ = "exchange_auth_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    exchange_name = Column(String, index=True)
    access_token = Column(LargeBinary)
    refresh_token = Column(LargeBinary)
    expires_in = Column(Integer)
    created_at = Column(TIMESTAMP, default=lambda: datetime.now(timezone.utc))
    scope = Column(String, nullable=True)
    

