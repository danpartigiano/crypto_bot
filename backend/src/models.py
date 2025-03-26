from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, LargeBinary, Boolean
from database import Base
from datetime import datetime, timezone


# holds user information for the crypto-bot platform
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(LargeBinary)
    active = Column(Boolean, default=True)

class OAuth_State(Base):

    __tablename__ = "oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))


# holds information about each supported exchange
class Exchange(Base):
    __tablename__ = "exchanges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

# holds authentication details like OAuth tokens and expiration dates for users to different platforms
class Exchange_Auth_Token(Base):
    __tablename__ = "exchange_auth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    exchange_id = Column(Integer, ForeignKey("exchanges.id"), index=True)
    access_token = Column(String)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=lambda: datetime.now(timezone.utc))
    scope = Column(String, nullable=True)