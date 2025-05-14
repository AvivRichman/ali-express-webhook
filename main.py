#!/usr/bin/env python3

import time
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify

# === CONFIG ===
APP_KEY     = "514792"
APP_SECRET  = "EFUG78khiSae7fPhQo5H0KB0uiJMlXTc"
ACCESS_TOKEN = ""
COUNTRY      = "IL"
TARGET_CURR  = "ILS"
TARGET_LANG  = "EN"
TRACKING_ID  = "default"
ENDPOINT     = "https://api-sg.aliexpress.com/sync"
RESULT_WEBHOOK = "https://hook.eu2.make.com/rysnctcvstd08ar6b0a4hcagsihwpw9a"  # ← הדבק כאן את הקולט שלך
# ==============

app = Flask(__name__)


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


def call_productdetail_api(product_id: str) -> dict:
    method = "aliexpress.affiliate.productdetail.get"
    extra = {
        "product_ids": product_id,
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
        "promotion_link_type": "0",
    }
    params = build_params(method, extra)
    params["sign"] = compute_sign(params)
    response = requests.get(ENDPOINT, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    try:
        return "222", data["aliexpress_affiliate_link_generate_response"]["resp_result"]["result"]["promotion_links"][0]["short_link_url"]
    except Exception:
        return "111"


@app.route("/run", methods=["POST"])
def run_affiliate_process():
    print("✅ התחיל תהליך /run")
    try:
        if not request.is_json:
            print("❌ הבקשה אינה JSON חוקי")
            return jsonify({"error": "Request must be JSON"}), 400

        content = request.get_json(force=True)
        print("📦 תוכן הבקשה:", content)

        product_id = content.get("product_id")
        if not product_id:
            print("❌ חסר product_id")
            return jsonify({"error": "Missing product_id"}), 400

        product_url = f"https://www.aliexpress.com/item/{product_id}.html"
        print("🔗 URL:", product_url)

        detail_data = call_productdetail_api(product_id)
        print("🔍 פרטי מוצר הוחזרו")

        short_link = generate_short_affiliate_link(product_url)
        print("🔗 קישור שותף נוצר:", short_link)

        payload = {
            "product_id": product_id,
            "short_link": short_link,
            "product_url": product_url,
            "details": detail_data
        }

        print("📤 שולח את הנתונים ל-Make...")
        response = requests.post(RESULT_WEBHOOK, json=payload)
        print("✅ נשלח ל-Make:", response.status_code)

        return jsonify({"status": "processed", "product_id": product_id}), 200

    except Exception as e:
        print("❌ שגיאה בשרת:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
