#!/usr/bin/env python3

import time
import os
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify

# === CONFIG ===
APP_KEY     = os.getenv("APP_KEY")
APP_SECRET  = os.getenv("APP_SECRET")
ACCESS_TOKEN = ""
COUNTRY      = "IL"
TARGET_CURR  = "ILS"
TARGET_LANG  = "EN"
TRACKING_ID  = "default"
ENDPOINT     = "https://api-sg.aliexpress.com/sync"
RESULT_WEBHOOK_WHATSAPP = os.getenv("RESULT_WEBHOOK_WHATSAPP")
RESULT_WEBHOOK_TELEGRAM = os.getenv("RESULT_WEBHOOK_TELEGRAM")
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

def get_hot_product():
    method = "aliexpress.affiliate.hotproduct.query"
    extra = {
        "page_no": 1,
        "page_size": 1,  # מוצר אחד בלבד
        "target_currency": TARGET_CURR,
        "target_language": TARGET_LANG,
        "tracking_id": TRACKING_ID,
        "ship_to_country": COUNTRY,
        "sort": "LAST_VOLUME_DESC",  # הכי נמכר
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
        return data
    except Exception:
        return "error at generate affiliate link"


@app.route("/run_whatsapp", methods=["POST"])
def run_affiliate_process():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        content = request.get_json(force=True)

        product_id = content.get("product_id")
        if not product_id:
            return jsonify({"error": "Missing product_id"}), 400

        product_url = f"https://www.aliexpress.com/item/{product_id}.html"

        detail_data = call_productdetail_api(product_id)

        short_link = generate_short_affiliate_link(product_url)

        payload = {
            "product_id": product_id,
            "short_link": short_link,
            "product_url": product_url,
            "details": detail_data
        }

        response = requests.post(RESULT_WEBHOOK_WHATSAPP, json=payload)

        return jsonify({"status": "processed", "product_id": product_id}), 200

    except Exception as e:
        print("❌ שגיאה בשרת:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/send_hot_product", methods=["POST"])
def send_hot_product():
    try:
        data = get_hot_product()
        product_list = data.get("resp_result", {}).get("result", {}).get("products", [])
        
        return data, product_list
        
        if not product_list:
            return jsonify({"error": "No hot products found"}), 404

        product = product_list[0]  # ניקח את הראשון
        product_id = product.get("product_id")
        product_url = product.get("product_url")

        # ניצור קישור שותף קצר
        short_link = generate_short_affiliate_link(product_url)

        payload = {
            "product_id": product_id,
            "short_link": short_link,
            "product_url": product_url,
            "details": product
        }

        response = requests.post(RESULT_WEBHOOK_TELEGRAM, json=payload)

        return jsonify({"status": "sent", "product_id": product_id}), 200

    except Exception as e:
        print("❌ שגיאה במשלוח מוצר חם:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/run_telegram", methods=["POST"])
def run_affiliate_process_telegram():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        content = request.get_json(force=True)

        product_id = content.get("product_id")
        if not product_id:
            return jsonify({"error": "Missing product_id"}), 400

        product_url = f"https://www.aliexpress.com/item/{product_id}.html"

        detail_data = call_productdetail_api(product_id)

        short_link = generate_short_affiliate_link(product_url)

        payload = {
            "product_id": product_id,
            "short_link": short_link,
            "product_url": product_url,
            "details": detail_data
        }

        response = requests.post(os.getenv("RESULT_WEBHOOK_TELEGRAM"), json=payload)

        return jsonify({"status": "processed", "product_id": product_id}), 200

    except Exception as e:
        print("❌ שגיאה בשרת:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
