from sqlalchemy import Column, Integer, String, LargeBinary, Boolean, TIMESTAMP
from app.services.database import Base
from datetime import datetime, timezone
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(LargeBinary)
    created_at = Column(TIMESTAMP, default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    active = Column(Boolean, default=True)

    def __str__(self) -> str:
        return self.username
    

    @classmethod
    async def by_username(cls, db: AsyncSession, username: str) -> "User":
        query = select(cls).filter_by(username=username)
        result = await db.execute(query)
        return result.first()

    
    #add any other useful methods for this class here, __eq__()?


    

