import os
import requests
import time
import hmac
import hashlib
from flask import Flask, request

# ===== CONFIG =====
ACCESS_ID = os.environ["ACCESS_ID"]
ACCESS_SECRET = os.environ["ACCESS_SECRET"]
DEVICE_ID = os.environ["DEVICE_ID"]
REGION = os.environ.get("REGION", "eu")
BOT_TOKEN = os.environ["BOT_TOKEN"]

CHAT_IDS = set()
# ============================
def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def hmac_sha256_upper(key: str, msg: str) -> str:
    return hmac.new(
        key.encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha256
    ).hexdigest().upper()

def get_access_token():
    method = "GET"
    path = "/v1.0/token?grant_type=1"
    body = ""  # GET → empty body
    t = str(int(time.time() * 1000))
    string_to_sign = (
        ACCESS_ID +
        t +
        method + "\n" +
        sha256_hex(body) + "\n\n" +
        path
    )
    sign = hmac_sha256_upper(ACCESS_SECRET, string_to_sign)
    headers = {
        "client_id": ACCESS_ID,
        "sign": sign,
        "t": t,
        "sign_method": "HMAC-SHA256"
    }
    url = f"https://openapi.tuya{REGION}.com{path}"
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise Exception(f"Token error: {data}")
    return data["result"]["access_token"]

def get_device_online():
    access_token = get_access_token()
    method = "GET"
    path = f"/v1.0/iot-03/devices/{DEVICE_ID}"
    body = ""
    t = str(int(time.time() * 1000))
    string_to_sign = (
        ACCESS_ID +
        access_token +
        t +
        method + "\n" +
        sha256_hex(body) + "\n\n" +
        path
    )
    sign = hmac_sha256_upper(ACCESS_SECRET, string_to_sign)
    headers = {
        "client_id": ACCESS_ID,
        "access_token": access_token,
        "sign": sign,
        "t": t,
        "sign_method": "HMAC-SHA256"
    }
    url = f"https://openapi.tuya{REGION}.com{path}"
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise Exception(f"Device error: {data}")
    return data["result"]["online"]

def send_telegram(msg):
    for chat_id in CHAT_IDS:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=10
        )

# ===== FLASK APP =====
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").strip()
        if text == "/start":
            CHAT_IDS.add(chat_id)
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                          data={"chat_id": chat_id, "text": "Вас додано до сповіщень!"})
    return "OK", 200

@app.route("/check", methods=["GET"])
def check_status():
    online = get_device_online()
    status = "online ✅" if online else "offline ❌"
    send_telegram(f"Tuya розетка: {status}")
    return {"status": status}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
        save_state(current)
