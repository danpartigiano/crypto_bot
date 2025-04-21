import os
import time
import http.client
import json
import uuid
from dotenv import load_dotenv

# Parameters
MIN_PRICE_CHANGE_24_HRS = 0.1
DEFAULT_PROFIT_TARGET   = 0.25
BASE_URL                = "api.coinbase.com"


class CoinbaseClient:
    def __init__(self, access_token: str):
        self.token = access_token

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        conn = http.client.HTTPSConnection(BASE_URL)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        body = json.dumps(payload) if payload is not None else None
        conn.request(method, path, body, headers)
        resp = conn.getresponse()
        raw = resp.read()
        if resp.status >= 400:
            raise RuntimeError(f"HTTP {resp.status} Error for {path}: {raw.decode()}")
        return json.loads(raw)

    def get_accounts(self) -> list[dict]:
        return self._request("GET", "/api/v3/brokerage/accounts").get("accounts", [])

    def get_products(self) -> list[dict]:
        return self._request("GET", "/api/v3/brokerage/products").get("products", [])

    def list_orders(self, side: str = None, status: str = None) -> list[dict]:
        qs = []
        if side:   qs.append(f"side={side}")
        if status: qs.append(f"status={status}")
        qstr = f"?{'&'.join(qs)}" if qs else ""
        return self._request("GET", f"/api/v3/brokerage/orders{qstr}").get("orders", [])

    def market_buy(self, product_id: str, quote_size: float) -> dict:
        payload = {
            "client_order_id": str(uuid.uuid4()),
            "product_id":       product_id,
            "side":             "BUY",
            "order_configuration": {
                "market_market_ioc": {
                    "quote_size": f"{quote_size:.2f}"
                }
            }
        }
        return self._request("POST", "/api/v3/brokerage/orders", payload)

    def limit_sell(self, product_id: str, base_size: float, limit_price: float) -> dict:
        payload = {
            "client_order_id": str(uuid.uuid4()),
            "product_id":       product_id,
            "side":             "SELL",
            "order_configuration": {
                "limit_limit_gtc": {
                    "base_size":   f"{base_size:.4f}",
                    "limit_price": f"{limit_price:.4f}"
                }
            }
        }
        return self._request("POST", "/api/v3/brokerage/orders", payload)


def main():
    load_dotenv()
    token = os.getenv("ACCESS_TOKEN")
    if not token:
        raise RuntimeError("ACCESS_TOKEN must be set in .env")

    # Profit target override
    try:
        profit_target = float(os.getenv("TARGET_PROFIT") or DEFAULT_PROFIT_TARGET)
    except ValueError:
        print("Invalid TARGET_PROFIT, defaulting to 25%")
        profit_target = DEFAULT_PROFIT_TARGET

    client = CoinbaseClient(token)

    # Fetch USDC balance
    accounts = client.get_accounts()
    usdc_acc = next((a for a in accounts if a["currency"] == "USDC"), None)
    if not usdc_acc:
        raise RuntimeError("USDC account not found")
    total_balance = float(usdc_acc["available_balance"]["value"])

    # Exclude any products already on open SELL orders
    open_orders = client.list_orders(side="SELL", status="OPEN")
    selling_ids = {o["product_id"] for o in open_orders}

    # Find buy candidates
    products = client.get_products()
    to_buy = [
        p for p in products
        if p["product_id"].endswith("USD")
        and float(p["price_percentage_change_24h"]) > MIN_PRICE_CHANGE_24_HRS
        and p["product_id"] not in selling_ids
    ]

    if not to_buy:
        print("No products met the buy criteria.")
        print(f"Your USDC balance: {total_balance:.2f}")
        return

    # Allocate roughly equal funds (with a small 2% buffer)
    count      = len(to_buy)
    allocation = (total_balance / count) * 0.98
    # Ensure at least $1 per order
    while allocation <= 1 and count > 1:
        count -= 1
        allocation = total_balance / count

    for p in to_buy[:count]:
        pid          = p["product_id"]
        buy_price    = float(p["price"])
        quote_inc    = float(p["quote_increment"])
        quote_amt    = round(allocation + quote_inc, 2)

        if quote_amt > total_balance:
            print(f"Skipping {pid}: need {quote_amt}, have {total_balance:.2f}")
            continue

        print(f"▶ Buying {pid}: ${quote_amt}")
        buy_resp = client.market_buy(pid, quote_amt)
        print("  Buy response:", buy_resp)
        time.sleep(5)

        # Refresh balances to find how much base currency we now hold
        accounts = client.get_accounts()
        base     = pid.split("-")[0]
        base_acc = next((a for a in accounts if a["currency"] == base), None)
        qty      = float(base_acc["available_balance"]["value"]) if base_acc else 0.0

        if qty <= 0:
            print(f"No {base} to sell after buy.")
            continue

        limit_price = round(buy_price * (1 + profit_target), 4)
        print(f"Scheduling sell {pid}: {qty:.4f} @ {limit_price}")
        sell_resp = client.limit_sell(pid, qty, limit_price)
        print("  Sell response:", sell_resp)
        time.sleep(2)


if __name__ == "__main__":
    main()
# import os
# import time
# from dotenv import load_dotenv
# from coinbase.rest import RESTClient
# import uuid

# # Threshold for 24h price change
# MIN_PRICE_CHANGE_24_HRS = 0.1
# # Default profit target if none provided (25%)
# DEFAULT_PROFIT_TARGET = 0.25


# def main():
#     # Load environment variables
#     load_dotenv()
#     api_key = os.getenv("API_KEY")
#     api_secret = os.getenv("API_SECRET")
#     if not api_key or not api_secret:
#         raise RuntimeError("API_KEY and API_SECRET must be set in .env")

#     # Determine profit target (env var overrides default)
#     profit_env = os.getenv("TARGET_PROFIT")
#     try:
#         profit_target = float(profit_env) if profit_env is not None else DEFAULT_PROFIT_TARGET
#     except ValueError:
#         print(f"Invalid TARGET_PROFIT '{profit_env}', using default {DEFAULT_PROFIT_TARGET}")
#         profit_target = DEFAULT_PROFIT_TARGET

#     client = RESTClient(api_key=api_key, api_secret=api_secret, verbose=False)

#     # Locate USDC wallet ID (from env or via API)
#     wallet_id = os.getenv("USDC_WALLET_ID")
#     if not wallet_id:
#         accounts = client.get_accounts().get('accounts', [])
#         for acct in accounts:
#             if acct.get('currency') == 'USDC':
#                 wallet_id = acct.get('uuid')
#                 break
#     if not wallet_id:
#         raise RuntimeError("USDC wallet not found")

#     # Fetch open sell orders to exclude
#     open_orders = client.list_orders(order_side="SELL", order_status=["OPEN"]).get('orders', [])
#     selling_ids = {o['product_id'] for o in open_orders}

#     # Identify buy candidates
#     to_buy = []
#     spot_list = client.get_products(product_type="SPOT").get('products', [])
#     for p in spot_list:
#         pid = p['product_id']
#         change = float(p['price_percentage_change_24h'])
#         if pid.endswith("USD") and change > MIN_PRICE_CHANGE_24_HRS and pid not in selling_ids:
#             to_buy.append(p)

#     # Fetch USDC balance
#     accounts = client.get_accounts().get('accounts', [])
#     usdc_acc = next((a for a in accounts if a['currency'] == 'USDC'), None)
#     total_balance = float(usdc_acc['available_balance']['value']) if usdc_acc else 0.0

#     count = len(to_buy)
#     if count == 0:
#         print("No products met the buy criteria.")
#         print(f"Your wallet balance: {total_balance}")
#         return

#     # Allocate funds per trade (with 2% buffer)
#     allocation = (total_balance / count) * 0.98
#     # Ensure minimum $1 per order
#     while allocation <= 1 and count > 1:
#         count -= 1
#         allocation = total_balance / count

#     # Execute trades and schedule sells
#     for p in to_buy[:count]:
#         pid = p['product_id']
#         buy_price = float(p['price'])
#         inc = float(p['quote_increment'])
#         quote_amt = round(allocation + inc, 2)

#         # Refresh USDC balance
#         accounts = client.get_accounts().get('accounts', [])
#         usdc_acc = next((a for a in accounts if a['currency'] == 'USDC'), None)
#         balance = float(usdc_acc['available_balance']['value']) if usdc_acc else 0.0

#         if quote_amt > balance:
#             print(f"Skipping {pid}: need {quote_amt}, have {balance}")
#             continue

#         # Place market buy
#         order_ref = str(uuid.uuid4())
#         client.market_order_buy(
#             client_order_id=order_ref,
#             product_id=pid,
#             quote_size=str(quote_amt)
#         )
#         time.sleep(5)

#         # Schedule limit sell with chosen profit target
#         schedule_sell(client, pid, buy_price, profit_target)
#         time.sleep(2)


# def schedule_sell(client, product_id, buy_price, profit):
#     base = product_id.split("-")[0]
#     accounts = client.get_accounts().get('accounts', [])
#     base_acc = next((a for a in accounts if a['currency'] == base), None)
#     if not base_acc:
#         print(f"No wallet for {base}, skipping sell.")
#         return

#     qty = round(float(base_acc['available_balance']['value']), 4)
#     if qty <= 0:
#         print(f"No {base} to sell.")
#         return

#     limit_price = round(buy_price * (1 + profit), 4)
#     client.limit_order_gtc_sell(
#         client_order_id=str(uuid.uuid4()),
#         product_id=product_id,
#         base_size=str(qty),
#         limit_price=str(limit_price)
#     )


# if __name__ == "__main__":
#     main() 