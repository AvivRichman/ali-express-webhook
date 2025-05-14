#!/usr/bin/env python3
"""
AliExpress Affiliate – productdetail.get + short link generation (with Google Sheets)
"""

import time
import hmac
import hashlib
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ------------------------------------------------------------------
# ▶️ CONFIG –– החלף בערכים שלך
APP_KEY     = "514792"
APP_SECRET  = "EFUG78khiSae7fPhQo5H0KB0uiJMlXTc"
ACCESS_TOKEN = ""
COUNTRY      = "IL"
TARGET_CURR  = "ILS"
TARGET_LANG  = "EN"
TRACKING_ID  = "default"
ENDPOINT     = "https://api-sg.aliexpress.com/sync"
SHEET_URL    = "https://docs.google.com/spreadsheets/d/17M0s9gbjR9XlHWuUe0lpQxYsrF4rhM2ej-mMU8oCDFQ/edit"
CREDENTIALS_PATH = "/etc/secrets/service_account.json"  # נתיב ל־Render
# ------------------------------------------------------------------


def get_product_ids_from_sheet(sheet_url: str, credentials_path: str) -> list:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).sheet1
    ids = sheet.col_values(1)
    return [pid.strip() for pid in ids if pid.strip().isdigit()]


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

    print(data)

    try:
        return data["aliexpress_affiliate_link_generate_response"]["resp_result"]["result"]["promotion_links"][0]["short_link_url"]
    except Exception as e:
        return "❌ קישור שותף לא נוצר"


if __name__ == "__main__":
    try:
        product_ids = get_product_ids_from_sheet(SHEET_URL, CREDENTIALS_PATH)
        for pid in product_ids:
            PRODUCT_ID = pid
            data = call_productdetail_api(PRODUCT_ID)
            print(f"\n🔎 תוצאת API עבור מוצר {PRODUCT_ID}:\n", data)

            product_url = f"https://www.aliexpress.com/item/{PRODUCT_ID}.html"
            short_link = generate_short_affiliate_link(product_url)
            print(f"🔗 קישור מקוצר למוצר {PRODUCT_ID}:", short_link)

    except requests.HTTPError as e:
        print("HTTP error:", e.response.status_code, e.response.text)
    except Exception as exc:
        print("Error:", exc)
