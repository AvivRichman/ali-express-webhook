#!/usr/bin/env python3

import time
import hmac
import hashlib
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === CONFIGURATION ===
APP_KEY     = "514792"
APP_SECRET  = "EFUG78khiSae7fPhQo5H0KB0uiJMlXTc"
ACCESS_TOKEN = ""
TRACKING_ID  = "default"
ENDPOINT     = "https://api-sg.aliexpress.com/sync"

SHEET_URL   = "https://docs.google.com/spreadsheets/d/17M0s9gbjR9XlHWuUe0lpQxYsrF4rhM2ej-mMU8oCDFQ/edit"
CREDENTIALS_PATH = "/etc/secrets/service_account.json"  # ✅ נתיב מותאם ל־Render
MAKE_WEBHOOK = "https://hook.eu2.make.com/rysnctcvstd08ar6b0a4hcagsihwpw9a"
# ======================


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


def generate_short_affiliate_link(product_url: str) -> str:
    method = "aliexpress.affiliate.link.generate"
    extra = {
        "source_values": product_url,
        "tracking_id": TRACKING_ID,
        "promotion_link_type": "0",  # ✅ חובה לפי API
    }
    params = build_params(method, extra)
    params["sign"] = compute_sign(params)
    response = requests.get(ENDPOINT, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    try:
        return data["aliexpress_affiliate_link_generate_response"]["resp_result"]["result"]["promotion_links"][0]["short_link_url"]
    except Exception as e:
        print("❌ קישור שותף לא נוצר:", e)
        return None


def get_product_ids_from_sheet(sheet_url: str, credentials_path: str) -> list:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).sheet1
    ids = sheet.col_values(1)
    return [pid.strip() for pid in ids if pid.strip().isdigit()]


def send_to_make(payload: dict):
    try:
        r = requests.post(MAKE_WEBHOOK, json=payload)
        r.raise_for_status()
        print("✅ נשלח ל-Make:", payload)
    except Exception as e:
        print("❌ שגיאה בשליחה ל-Make:", e)


def main():
    product_ids = get_product_ids_from_sheet(SHEET_URL, CREDENTIALS_PATH)
    print(f"📦 נמצאו {len(product_ids)} מזהים")

    for pid in product_ids:
        product_url = f"https://www.aliexpress.com/item/{pid}.html"
        short_link = generate_short_affiliate_link(product_url)

        if short_link:
            payload = {
                "product_id": pid,
                "short_link": short_link
            }
            send_to_make(payload)
        else:
            print(f"⚠️ לא נוצר קישור למוצר {pid}")

    print("🎉 הסתיים התהליך בהצלחה.")


if __name__ == "__main__":
    main()
