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
    user_id = Column(Integer, ForeignKey("users.id"))
    

