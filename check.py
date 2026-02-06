import requests
import json
import os
import time
import hmac
import hashlib

# ====== CONFIG ======
ACCESS_ID = "TUYA_ACCESS_ID"
ACCESS_SECRET = "TUYA_ACCESS_SECRET"
DEVICE_ID = "TUYA_DEVICE_ID"
REGION = "eu"  # eu / us / cn

BOT_TOKEN = "TELEGRAM_BOT_TOKEN"
CHAT_ID = "TELEGRAM_CHAT_ID"

STATE_FILE = "/tmp/tuya_socket_state.txt"
# ====================


def tuya_headers():
    t = str(int(time.time() * 1000))
    sign = hmac.new(
        ACCESS_SECRET.encode(),
        (ACCESS_ID + t).encode(),
        hashlib.sha256
    ).hexdigest().upper()

    return {
        "client_id": ACCESS_ID,
        "sign": sign,
        "t": t,
        "sign_method": "HMAC-SHA256"
    }


def get_device_status():
    url = f"https://openapi.tuya{REGION}.com/v1.0/devices/{DEVICE_ID}"
    r = requests.get(url, headers=tuya_headers(), timeout=10)
    r.raise_for_status()
    return r.json()["result"]["online"]


def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg
    }, timeout=10)


def load_prev_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE) as f:
        return f.read().strip()


def save_state(state):
    with open(STATE_FILE, "w") as f:
        f.write(state)


def main():
    online = get_device_status()
    current = "online" if online else "offline"
    prev = load_prev_state()

    if prev != current:
        emoji = "✅" if online else "❌"
        send_telegram(f"Розетка {current.upper()} {emoji}")
        save_state(current)


if __name__ == "__main__":
    main()
