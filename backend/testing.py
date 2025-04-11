from app.utility.environment import environment
from authlib.integrations.requests_client import OAuth2Session
from datetime import datetime, timezone
from hashlib import blake2b
from coinbase.wallet.client import OAuthClient




oauth_session_coinbase = OAuth2Session(
    client_id=environment.COINBASE_CLIENT_ID,
    client_secret=environment.COINBASE_CLIENT_SECRET,
    redirect_uri=environment.COINBASE_REDIRECT_URI,
    scope=environment.COINBASE_CLIENT_TOKEN_SCOPE,
    )


# https://www.coinbase.com/oauth/authorize?response_type=code&client_id=0627e52c-15f4-4304-90bb-519ee6af7c89&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcoinbase%2Fcallback&scope=wallet%3Aaccounts%3Aread%2Cwallet%3Auser%3Aread%2Cwallet%3Atransactions%3Aread%2Cwallet%3Aorders%3Acreate%2Cwallet%3Atrades%3Aread%2Coffline_access&state=S26ubk6jmHOCmpQpsPyp7hBu0xxqu8
# RVPxifVf8nEg2Z45C82UOTaSw9B7j2kuENHIAkeenBs.DBJWLhD3uDulN7eZR0Q_B8sJLOYy3hkn3qG9aKkaCMs
# _yBN7Zwers0mbN7ybs1vtkwcw5j07qqXHWKo4RxIGr4.6OFloNxfE2dPOcBTbNizsv-Tc3Kha4B0-qecLNRQSLo
#it is find to 401 fail using an access token, but
#it is not fine to make multiple refresh requests using the same refresh token because that will invalidate the current refresh token
#   meaning no more refreshes


# https://www.coinbase.com/oauth/authorize?response_type=code&client_id=0627e52c-15f4-4304-90bb-519ee6af7c89&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcoinbase%2Fcallback&scope=wallet%3Aaccounts%3Aread%2Cwallet%3Auser%3Aread%2Cwallet%3Atransactions%3Aread%2Cwallet%3Aorders%3Acreate%2Cwallet%3Atrades%3Aread%2Coffline_access&state=BxPve78gakSPnPMQfHYiQWwoIANUSJ

# {'user_id': 1, 'exchange_name': 'coinbase', 'access_token': <psycopg2.extensions.Binary object at 0x0000024C731F6EE0>, 'refresh_token': <psycopg2.extensions.Binary object at 0x0000024C731F7150>, 'expires_at': 1744407228, 'created_at': datetime.datetime(2025, 4, 11, 20, 33, 48, 460298, tzinfo=datetime.timezone.utc), 'scope': 'wallet:accounts:read wallet:user:read wallet:transactions:read wallet:orders:create wallet:trades:read offline_access', 'refresh_attempts': 0}

# response = oauth_session_coinbase.refresh_token(url=environment.COINBASE_TOKEN_URL, refresh_token="_yBN7Zwers0mbN7ybs1vtkwcw5j07qqXHWKo4RxIGr4.6OFloNxfE2dPOcBTbNizsv-Tc3Kha4B0-qecLNRQSLo")

# https://www.coinbase.com/oauth/authorize?response_type=code&client_id=0627e52c-15f4-4304-90bb-519ee6af7c89&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcoinbase%2Fcallback&scope=wallet%3Aaccounts%3Aread%2Cwallet%3Auser%3Aread%2Cwallet%3Atransactions%3Aread%2Cwallet%3Aorders%3Acreate%2Cwallet%3Atrades%3Aread%2Coffline_access&state=rQkadasdDS3bmQgyVDBfW7l4hNWTfY

# {'user_id': 1, 'exchange_name': 'coinbase', 'access_token': <psycopg2.extensions.Binary object at 0x000002A7FCE45590>, 'refresh_token': <psycopg2.extensions.Binary object at 0x000002A7FCE453B0>, 'expires_at': 1744407519, 'created_at': 1744403919, 'scope': 'wallet:accounts:read wallet:user:read wallet:transactions:read wallet:orders:create wallet:trades:read offline_access', 'refresh_attempts': 0}

print(int(datetime.now(timezone.utc).timestamp()))
