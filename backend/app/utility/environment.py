from decouple import config
from pydantic_settings import BaseSettings


class Environment(BaseSettings):
    JWT_SECRET_KEY: str = config("JWT_SECRET_KEY", cast=str)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    POSTGRESQL_CONNECTION_STRING: str = config("POSTGRESQL_CONNECTION_STRING", cast=str)
    COINBASE_CLIENT_ID: str = config("COINBASE_CLIENT_ID", cast=str)
    COINBASE_CLIENT_SECRET: str = config("COINBASE_CLIENT_SECRET", cast=str)
    COINBASE_REDIRECT_URI: str = config("COINBASE_REDIRECT_URI", cast=str)
    PRODUCTION: bool = config("PRODUCTION", cast=bool)
    

environment = Environment()