from pydantic import AnyHttpUrl
from decouple import config
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_STR: str = "/api"
    JWT_SECRET_KEY: str = config("JWT_SECRET_KEY", cast=str)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost"]
    PROJECT_NAME: str = "CryptoBot"
    POSTGRESQL_CONNECTION_STRING: str = config("POSTGRESQL_CONNECTION_STRING", cast=str)
    COINBASE_CLIENT_ID: str = config("COINBASE_CLIENT_ID", cast=str)
    COINBASE_CLIENT_SECRET: str = config("COINBASE_CLIENT_SECRET", cast=str)
    COINBASE_REDIRECT_URI: str = config("COINBASE_REDIRECT_URI", cast=str)



    class Config:
        case_sensitive = True
    

settings = Settings()


# JWT_REFRESH_SECRET_KEY: str = config("JWT_REFRESH_SECRET_KEY", cast=str)
    # REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

print(settings.model_dump_json)