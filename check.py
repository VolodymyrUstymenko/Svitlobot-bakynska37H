import os
import requests
import time
import hmac
import hashlib
import json

# ========== CONFIG ==========
ACCESS_ID = os.environ["ACCESS_ID"]
ACCESS_SECRET = os.environ["ACCESS_SECRET"]
DEVICE_ID = os.environ["DEVICE_ID"]
REGION = os.environ.get("REGION", "eu")
BOT_TOKEN = os.environ["BOT_TOKEN"]

STATE_FILE = "state.txt"
USERS_FILE = "users.txt"
GETUPDATES_FILE = "last_update_id.txt"  # для зберігання останнього update_id
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

def load_prev_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        return f.read().strip()

def save_state(state):
    with open(STATE_FILE, "w") as f:
        f.write(state)

def get_last_update_id():
    if not os.path.exists(GETUPDATES_FILE):
        return None
    with open(GETUPDATES_FILE, "r") as f:
        return f.read().strip()

def save_last_update_id(update_id):
    with open(GETUPDATES_FILE, "w") as f:
        f.write(str(update_id))

def get_chat_ids():
    chat_ids = set()
    # зберігаємо всіх користувачів у файлі
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            chat_ids.update(f.read().splitlines())
    return chat_ids

def add_chat_id(chat_id):
    chat_ids = get_chat_ids()
    chat_ids.add(str(chat_id))
    with open(USERS_FILE, "w") as f:
        f.write("\n".join(chat_ids))

def poll_updates():
    last_update_id = get_last_update_id()
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout=5"
    if last_update_id:
        url += f"&offset={int(last_update_id)+1}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
    updates = data.get("result", [])
    for upd in updates:
        update_id = upd["update_id"]
        message = upd.get("message")
        if message and "text" in message:
            text = message["text"]
            chat_id = message["chat"]["id"]
            if text.strip() == "/start":
                add_chat_id(chat_id)
        save_last_update_id(update_id)

def send_telegram(msg):
    chat_ids = get_chat_ids()
    for chat_id in chat_ids:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=10
        )

def main():
    # спочатку обробляємо нових користувачів
    poll_updates()
    # перевірка стану Tuya
    online = get_device_online()
    current = "online" if online else "offline"
    prev = load_prev_state()
    if prev != current:
        emoji = "✅" if online else "❌"
        send_telegram(f"Tuya розетка: {current.upper()} {emoji}")
        save_state(current)

if __name__ == "__main__":
    main()
