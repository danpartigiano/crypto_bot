from fastapi import HTTPException
from app.database.models import OAuth_State, User
from typing import Union
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.utility.environment import environment
from app.utility.TokenService import TokenService
import http.client
import json
import logging



logger = logging.getLogger()

@staticmethod
def get_state_by_state(state: str, db: Session) -> Union[OAuth_State, None]:
    result = db.execute(select(OAuth_State).where(OAuth_State.state == state))
    return result.scalars().first()

@staticmethod
def get_state_by_user_id(user_id: str, db: Session) -> Union[OAuth_State, None]:
    result = db.execute(select(OAuth_State).where(OAuth_State.user_id == user_id))
    return result.scalars().first()

@staticmethod
def store_state_in_db(user: User, state: str, db: Session) -> Union[OAuth_State, None]:

    #link the state to the current user in the database
    new_oauth_state = OAuth_State(state=state, user_id=user.id)

    try:
        db.add(new_oauth_state)
        db.commit()
        return new_oauth_state

    except SQLAlchemyError as e:
        db.rollback()
        return None

@staticmethod
def remove_state(state: OAuth_State, db: Session) -> Union[OAuth_State, None]:
    try:
        db.delete(state)
        db.commit()
        return state
    
    except SQLAlchemyError as e:
        logger.error(f"Error deleting state for {state.user_id}")
        db.rollback()
        return None
    
@staticmethod
def clear_all_states_for_user(user: User, db: Session) -> bool:
    try:
        db.query(OAuth_State).filter(OAuth_State.user_id == user.id).delete(synchronize_session=False)
        db.commit()
        return True
    
    except SQLAlchemyError as e:
        logger.error(f"Error deleting state for {user.username}")
        db.rollback()
        return False
    
@staticmethod
def get_callback_status_page(error_message: HTTPException | None):
    "Returns an html page used to show if the client's coinbase oauth exchange was successful"

    circle_color = "green"
    message = "Coinbase Account Linked to Crypto Bot!"
    symbol = "&#x2714"

    if error_message is not None:
        #there was an error
        circle_color = "red"
        message = f"HTTP ERROR {error_message.status_code}: {error_message.detail}"
        symbol = "&#10060"


    webpage = f"""
        <html>
            <head><title>Coinbase OAuth Status</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: black;">
                <div style="margin-bottom: 20px;">
                    <div style="background-color: {circle_color}; color: white; 
                                width: 150px; height: 150px; 
                                border-radius: 50%; display: flex; justify-content: center; align-items: center; 
                                font-size: 100px; margin: 0 auto;">
                        {symbol}
                    </div>
                </div>
                <h2 style="color: white;">{message}</h2>
                <br>
            </body>
        </html>
        """

    return webpage

@staticmethod
def get_user_portfolios(user: User, db: Session) -> Union[dict, None]:

    if user is None:
        return None
    
    token_service = TokenService(user_id=user.id, db=db)

    coinbase_access_token = token_service.get_access_token(exchange_name="coinbase")

    if coinbase_access_token is None:
        return None


    try:
        #get all portfolios
        conn = http.client.HTTPSConnection("api.coinbase.com")
        payload = ''
        headers = {
            "Authorization": f"Bearer {coinbase_access_token}",
            "Content-Type": "application/json"
        }
        conn.request("GET", "/api/v3/brokerage/portfolios", payload, headers)
        res = conn.getresponse().read().decode("utf-8")
        data = json.loads(res)


        #get the balances for each active portfolio
        all_portfolio_data = dict()
        all_portfolio_data.update({"portfolios": []})


        for portfolio in data["portfolios"]:
            if portfolio["deleted"] == False:
                portfolio_uuid = portfolio["uuid"]
                conn.request("GET", f"/api/v3/brokerage/portfolios/{portfolio_uuid}", payload, headers)
                res = conn.getresponse().read().decode("utf-8")
                data = json.loads(res)
                all_portfolio_data["portfolios"].append(data["breakdown"])

        return all_portfolio_data

    except Exception as e:
        logger.error(f"{e}")
        return None

    