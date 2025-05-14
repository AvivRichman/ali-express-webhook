#!/usr/bin/env python3
"""
AliExpress Affiliate – productdetail.get
Test script for one‑off debugging outside Make.com
"""

import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from flask import Flask
import threading

# ------------------------------------------------------------------
# ▶️  CONFIG –– החלף בערכים שלך
APP_KEY     = "514792"
APP_SECRET  = "EFUG78khiSae7fPhQo5H0KB0uiJMlXTc"
ACCESS_TOKEN = ""          # השאר ריק אם לא חובה בחשבונך
PRODUCT_IDS = "3256807779564847"   # פסיק בין IDs מרובים
COUNTRY     = "IL"
TARGET_CURR = "ILS"
TARGET_LANG = "EN"
TRACKING_ID = "default"
# ------------------------------------------------------------------

API_METHOD = "aliexpress.affiliate.productdetail.get"
ENDPOINT   = "https://api-sg.aliexpress.com/sync"


def build_params() -> dict:
    """Create the dict of parameters *excluding* the signature."""
    ts_ms = str(int(time.time() * 1000))   # 13‑digit Unix ms
    p = {
        "app_key":        APP_KEY,
        "method":         API_METHOD,
        "timestamp":      ts_ms,
        "sign_method":    "sha256",
        "v":              "2.0",
        "product_ids":    PRODUCT_IDS,
        "country":        COUNTRY,
        "target_currency":TARGET_CURR,
        "target_language":TARGET_LANG,
        "tracking_id":    TRACKING_ID,
    }
    if ACCESS_TOKEN:
        p["access_token"] = ACCESS_TOKEN
    return p


def compute_sign(params: dict) -> str:
    """Return HMAC‑SHA256 signature (HEX‑UPPER) over sorted param string."""
    sorted_items = sorted(params.items())           # ASCII order
    base_str = "".join(f"{k}{v}" for k, v in sorted_items)
    digest = hmac.new(APP_SECRET.encode("utf-8"),
                      base_str.encode("utf-8"),
                      hashlib.sha256).hexdigest().upper()
    return digest


def call_api():
    params = build_params()
    params["sign"] = compute_sign(params)
    # Optional debug:
    # print("Base string:", "".join(f"{k}{v}" for k,v in sorted(params.items()) if k!="sign"))
    resp = requests.get(ENDPOINT, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


# === ADD THIS FUNCTION ===
def send_to_make(payload: dict):
    webhook_url = "https://hook.eu2.make.com/rysnctcvstd08ar6b0a4hcagsihwpw9a"  # 👈 החלף בכתובת האמיתית שלך
    try:
        r = requests.post(webhook_url, json=payload)
        r.raise_for_status()
        print("✅ Data sent to Make successfully")
    except Exception as e:
        print("❌ Failed to send to Make:", str(e))


# === CHANGE MAIN TO THIS ===
if __name__ == "__main__":
    try:
        data = call_api()
        send_to_make(data)  # 👈 שלח את הפלט ל-Make
    except requests.HTTPError as e:
        print("HTTP error:", e.response.status_code, e.response.text)
    except Exception as exc:
        print("Error:", exc)


app = Flask(__name__)

@app.route("/")
def run_script():
    try:
        data = call_api()
        send_to_make(data)
        return "✅ Success – Data sent to Make", 200
    except Exception as e:
        return f"❌ Error: {str(e)}", 500

def run_flask():
    app.run(host="0.0.0.0", port=3000)

# Start Flask in separate thread so Replit stays alive
threading.Thread(target=run_flask).start()
