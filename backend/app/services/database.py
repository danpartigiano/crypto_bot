from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.sql import text
from app.core.config import settings


DATABASE_URL = settings.POSTGRESQL_CONNECTION_STRING

engine = create_async_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(autocommit=False, class_=AsyncSession, autoflush=False, bind=engine)

Base = declarative_base()

async def get_session() -> AsyncSession:
    async with SessionLocal() as db:
        yield db


async def db_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  #Only for development purposes
        await conn.run_sync(Base.metadata.create_all)


async def db_shutdown() -> None:
    await engine.dispose()
