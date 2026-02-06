import requests
import os
import time
import hmac
import hashlib

# Tuya
ACCESS_ID = os.environ["ACCESS_ID"]
ACCESS_SECRET = os.environ["ACCESS_SECRET"]
DEVICE_ID = os.environ["DEVICE_ID"]
REGION = os.environ.get("REGION", "eu")
STATE_FILE = "state.txt"

# Telegram
BOT_TOKEN = os.environ["BOT_TOKEN"]
USERS_FILE = "users.txt"

def tuya_headers():
    t = str(int(time.time() * 1000))
    sign = hmac.new(
        ACCESS_SECRET.encode(),
        (ACCESS_ID + t).encode(),
        hashlib.sha256
    ).hexdigest().upper()
    return {"client_id": ACCESS_ID, "sign": sign, "t": t, "sign_method": "HMAC-SHA256"}

def get_device_online():
    url = f"https://openapi.tuya{REGION}.com/v1.0/devices/{DEVICE_ID}"
    r = requests.get(url, headers=tuya_headers(), timeout=10)
    r.raise_for_status()
    return r.json()["result"]["online"]

def load_prev_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        return f.read().strip()

def save_state(state):
    with open(STATE_FILE, "w") as f:
        f.write(state)

def get_chat_ids():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

def send_telegram(msg):
    chat_ids = get_chat_ids()
    for chat_id in chat_ids:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=10
        )

def main():
    online = get_device_online()
    current = "online" if online else "offline"
    prev = load_prev_state()
    if prev != current:
        emoji = "✅" if online else "❌"
        send_telegram(f"Tuya розетка: {current.upper()} {emoji}")
        save_state(current)

if __name__ == "__main__":
    main()
