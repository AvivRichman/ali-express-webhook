#!/usr/bin/env python3
"""
AliExpress Affiliate – productdetail.get + short link generation
"""

import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from flask import Flask
import threading

# ------------------------------------------------------------------
# ▶️ CONFIG –– החלף בערכים שלך
APP_KEY      = "514792"
APP_SECRET   = "EFUG78khiSae7fPhQo5H0KB0uiJMlXTc"
ACCESS_TOKEN = ""  # השאר ריק אם לא חובה
PRODUCT_IDS  = "1005005275950625"
COUNTRY      = "IL"
TARGET_CURR  = "ILS"
TARGET_LANG  = "EN"
TRACKING_ID  = "default"
ENDPOINT     = "https://api-sg.aliexpress.com/sync"
MAKE_WEBHOOK = "https://hook.eu2.make.com/rysnctcvstd08ar6b0a4hcagsihwpw9a"
# ------------------------------------------------------------------


def build_params(method: str, extra_params: dict = {}) -> dict:
    ts_ms = str(int(time.time() * 1000))
    params = {
        "app_key":     APP_KEY,
        "method":      method,
        "timestamp":   ts_ms,
        "sign_method": "sha256",
        "v":           "2.0",
    }
    if ACCESS_TOKEN:
        params["access_token"] = ACCESS_TOKEN
    params.update(extra_params)
    return params


def compute_sign(params: dict) -> str:
    sorted_items = sorted(params.items())
    base_str = "".join(f"{k}{v}" for k, v in sorted_items)
    digest = hmac.new(APP_SECRET.encode("utf-8"),
                      base_str.encode("utf-8"),
                      hashlib.sha256).hexdigest().upper()
    return digest


def call_productdetail_api() -> dict:
    method = "aliexpress.affiliate.productdetail.get"
    extra = {
        "product_ids": PRODUCT_IDS,
        "country": COUNTRY,
        "target_currency": TARGET_CURR,
        "target_language": TARGET_LANG,
        "tracking_id": TRACKING_ID,
    }
    params = build_params(method, extra)
    params["sign"] = compute_sign(params)
    response = requests.get(ENDPOINT, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def generate_short_affiliate_link(product_url: str) -> str:
    method = "aliexpress.affiliate.link.generate"
    extra = {
        "source_values": product_url,
        "tracking_id": TRACKING_ID,
    }
    params = build_params(method, extra)
    params["sign"] = compute_sign(params)
    response = requests.get(ENDPOINT, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    try:
        return data["aliexpress_affiliate_link_generate_response"]["resp_result"]["result"]["promotion_links"][0]["short_link_url"]
    except Exception:
        return "❌ קישור שותף לא נוצר"


def send_to_make(payload: dict):
    try:
        r = requests.post(MAKE_WEBHOOK, json=payload)
        r.raise_for_status()
        print("✅ Data sent to Make successfully")
    except Exception as e:
        print("❌ Failed to send to Make:", str(e))


# === MAIN EXECUTION FUNCTION ===
def main_process():
    data = call_productdetail_api()

    # שלוף URL מוצר + צור קישור שותף קצר
    try:
        product_url = data["aliexpress_affiliate_productdetail_get_response"]["result"]["products"][0]["product_url"]
        short_link = generate_short_affiliate_link(product_url)
        data["short_affiliate_link"] = short_link
    except Exception as e:
        data["short_affiliate_link"] = f"❌ לא נוצר קישור ({e})"

    send_to_make(data)


# === FOR LOCAL AND WEB RUNNING ===
app = Flask(__name__)

@app.route("/")
def run_script():
    try:
        main_process()
        return "✅ Success – Data sent to Make", 200
    except Exception as e:
        return f"❌ Error: {str(e)}", 500

def run_flask():
    app.run(host="0.0.0.0", port=3000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
