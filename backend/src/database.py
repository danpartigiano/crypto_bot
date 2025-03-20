from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import text


DATABASE_URL = 'postgresql://admin:password@localhost/crypto'

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# # Test the connection
# db = SessionLocal()
# try:
#     db.execute(text('SELECT 1'))
#     print("Connected to db")
# except Exception as e:
#     print(f"Connection failed: {e}")
# finally:
#     db.close()
