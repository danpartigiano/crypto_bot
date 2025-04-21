import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from app.utility.coinbase_helper import get_coinbase_balance
from app.utility.user_helper import get_current_user
from app.database.db_connection import get_session
from sqlalchemy.orm import Session

import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/balance")
async def websocket_balance_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")

    db = next(get_session())

    try:
        # Extract token from cookies
        token = websocket.cookies.get("token")
        logger.debug(f"Token from query params: {token}")

        if not token:
            await websocket.send_json({"error": "unauthorized: no token found"})
            await websocket.close(code=1008)
            return

        # Authenticate user using the token
        user = get_current_user(token, db)
        if not user:
            await websocket.send_json({"error": "unauthorized: invalid token"})
            await websocket.close(code=1008)
            return

        while True:
            # Get the user's balance
            balance = get_coinbase_balance(user, db)
            if isinstance(balance, dict) and 'error' in balance:
                await websocket.send_json({"error": balance['error']})
            else:
                await websocket.send_json({"balance": balance})
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception("Unexpected error in WebSocket")
        await websocket.close(code=1011)
    finally:
        db.close()