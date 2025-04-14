from decouple import config
from pydantic_settings import BaseSettings


class Environment(BaseSettings):
    JWT_SECRET_KEY: str = config("JWT_SECRET_KEY", cast=str)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    POSTGRESQL_CONNECTION_STRING: str = config("POSTGRESQL_CONNECTION_STRING", cast=str)

    # Coinbase vars
    COINBASE_CLIENT_ID: str = config("COINBASE_CLIENT_ID", cast=str)
    COINBASE_CLIENT_SECRET: str = config("COINBASE_CLIENT_SECRET", cast=str)
    COINBASE_REDIRECT_URI: str = config("COINBASE_REDIRECT_URI", cast=str)
    COINBASE_OAUTH_URL: str = config("COINBASE_OAUTH_URL", cast = str)
    COINBASE_TOKEN_URL: str = config("COINBASE_TOKEN_URL", cast = str)
    COINBASE_CLIENT_TOKEN_SCOPE: str = config("COINBASE_CLIENT_TOKEN_SCOPE", cast = str)
    COINBASE_TOKEN_ENCRYPTION_KEY: str = config("COINBASE_TOKEN_ENCRYPTION_KEY", cast = str)

    # Redis vars
    REDIS_HOST: str = config("REDIS_HOST", cast=str, default="localhost")
    REDIS_PORT: int = config("REDIS_PORT", cast=int, default=6379)

    PRODUCTION: bool = config("PRODUCTION", cast=bool, default=False)
    

environment = Environment()