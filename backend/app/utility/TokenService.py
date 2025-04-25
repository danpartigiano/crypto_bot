from app.database.models import User, Exchange_Auth_Token
from typing import Union
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from sqlalchemy.future import select
from app.utility.environment import environment
from cryptography.fernet import Fernet
from authlib.integrations.requests_client import OAuth2Session
import random
from datetime import datetime, timezone
import logging



logger = logging.getLogger()


class TokenService:
    """Centralized Exchange Token Management Service"""

    def __init__(self, user_id: int, db: Session):
        self.id = random.randint(0, 999999)
        self.user_id = user_id
        self.db = db

    def get_access_token(self, exchange_name: str) -> Union[str, None]:
        """Gets the access token associated with this user and exchange"""

        token = (self.db.execute(select(Exchange_Auth_Token).where((Exchange_Auth_Token.user_id == self.user_id) & (Exchange_Auth_Token.exchange_name == exchange_name)))).scalars().first()

        #does this user have a token?
        if token is None:
            logger.info(f"User {self.user_id} does not have a {exchange_name} access token")
            return None

        #is this token still valid?
        if token.is_expired():
            logger.info(f"User {self.user_id} has an expired token {token.id} for exchange {exchange_name}")
            #refresh the token
            return self.__refresh_tokens(old_token=token)
        
        #if it is still valid then return the access token
        return TokenService.__decrypt(token.access_token)

    @staticmethod
    def __encrypt(data: str) -> bytes:
        cipher_suite = Fernet(environment.COINBASE_TOKEN_ENCRYPTION_KEY)
        return cipher_suite.encrypt(data.encode('utf-8'))

    @staticmethod
    def __decrypt(data: bytes) -> str:
        cipher_suite = Fernet(environment.COINBASE_TOKEN_ENCRYPTION_KEY)
        return cipher_suite.decrypt(data).decode('utf-8')


    def __refresh_tokens(self, old_token: Exchange_Auth_Token) -> Union[str, None]:

        #get the lock id for this user on the provided exchange
        lock_id = old_token.get_lock_id()


        #aquire the transaction level advisory lock, wait otherwise
        self.db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})
        logger.debug(f"{self.id} aquired lock {lock_id}")

        try:

            #check if we still need to update the token or if another process did it while we were waiting for the lock
            check_token = (self.db.execute(select(Exchange_Auth_Token).where((Exchange_Auth_Token.user_id == self.user_id) & (Exchange_Auth_Token.exchange_name == old_token.exchange_name)))).scalars().first()

            #is the token there?
            if check_token is None:
                logger.info(f"User {self.user_id} does not have a {old_token.exchange_name} access token to refresh")
                return None

            #does this token still need to be refreshed?
            if check_token.is_expired():
                logger.info(f"User {self.user_id} still has an expired token {check_token.id} for exchange {old_token.exchange_name}")

                #if this is the third attempt at a refresh, delete the token and require the user to re authenticate
                if check_token.refresh_attempts >= 3:
                    logger.error(f"Token {check_token.id} is being deleted, attempted refreshes is now {check_token.refresh_attempts}")
                    self.db.delete(check_token)
                    return None


                #update the refresh attempts for this token
                check_token.refresh_attempts += 1
                logger.info(f"Token {check_token.id} attempted refreshes is now {check_token.refresh_attempts}")
                self.db.commit()

                
                #refresh the token via oauth for the exchange
                

                match old_token.exchange_name:
                    case "coinbase":
                        oauth_session_coinbase = OAuth2Session(client_id=environment.COINBASE_CLIENT_ID, client_secret=environment.COINBASE_CLIENT_SECRET, redirect_uri=environment.COINBASE_REDIRECT_URI, scope=environment.COINBASE_CLIENT_TOKEN_SCOPE)

                        response = oauth_session_coinbase.refresh_token(url=environment.COINBASE_TOKEN_URL, refresh_token=TokenService.__decrypt(check_token.refresh_token))



                        new_access_token = response["access_token"]
                        new_refresh_token = response["refresh_token"]
                        new_scope = response["scope"]
                        new_expires_at = response["expires_at"]

                        check_token.access_token = TokenService.__encrypt(new_access_token)
                        check_token.refresh_token = TokenService.__encrypt(new_refresh_token)
                        check_token.scope = new_scope
                        check_token.expires_at = int(new_expires_at)
                        check_token.refresh_attempts = 0

                        self.db.commit()
                        logger.debug(f"{self.id} refreshed token {check_token.id}")
                        return new_access_token
                    

            else:
                #commit to release the lock
                self.db.commit()
                logger.debug(f"{self.id} released lock {lock_id}")
                return TokenService.__decrypt(check_token.access_token)


        except Exception as e:
            logger.debug(f"{self.id} released lock {lock_id}")
            logger.error(f"Error while refreshing token {old_token.id} for user {self.user_id}: {e}")
            self.db.rollback()
        return None


    def exchange_oauth_code_for_tokens(self, code: str, exchange_name: str) -> bool:
        """Exchange the provided code for tokens on the exchange (oauth)"""


        if code is None:
            logger.error(f"No code provided, can't get tokens for {self.user_id}")
            return False



        match exchange_name:
            case "coinbase":
                
                try:
                    oauth_session_coinbase = OAuth2Session(
                        client_id=environment.COINBASE_CLIENT_ID,
                        client_secret=environment.COINBASE_CLIENT_SECRET,
                        redirect_uri=environment.COINBASE_REDIRECT_URI,
                        scope=environment.COINBASE_CLIENT_TOKEN_SCOPE)

                    #exchange code for tokens, returns an OAuth2Token
                    coinbase_tokens = oauth_session_coinbase.fetch_token(
                        url=environment.COINBASE_TOKEN_URL,
                        method="POST",
                        grant_type="authorization_code",
                        code=code)
                    
                    new_exchange_token = Exchange_Auth_Token(
                        user_id = self.user_id,
                        exchange_name = exchange_name,
                        access_token = TokenService.__encrypt(coinbase_tokens["access_token"]),
                        refresh_token = TokenService.__encrypt(coinbase_tokens["refresh_token"]),
                        expires_at = int(coinbase_tokens["expires_at"]),
                        scope = coinbase_tokens["scope"]
                        )
                
                    self.db.add(new_exchange_token)
                    self.db.commit()
                    return True
                    

                except Exception as e:
                    logger.error(f"Error while getting new tokens for user {self.user_id}: {e}")
                    self.db.rollback()
                
        return False
 


