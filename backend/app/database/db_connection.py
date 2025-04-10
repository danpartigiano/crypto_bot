from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy import create_engine
from app.utility.environment import environment

DATABASE_URL = environment.POSTGRESQL_CONNECTION_STRING

engine = create_engine(DATABASE_URL, echo=(not environment.PRODUCTION))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
