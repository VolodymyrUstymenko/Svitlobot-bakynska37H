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

STATE_FILE = "state.txt"
CHAT_IDS = "chat_ids.txt"
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

def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE) as f:
        return f.read().strip()

def save_state(state: str):
    with open(STATE_FILE, "w") as f:
        f.write(state)

def load_chat_ids():
    if not os.path.exists(CHAT_IDS):
        return set()
    with open(CHAT_IDS) as f:
        return set(line.strip() for line in f if line.strip())

def save_chat_ids(chat_ids: set):
    with open(CHAT_IDS, "w") as f:
        f.write("\n".join(str(cid) for cid in chat_ids))
        
def send_telegram(msg):
    chat_ids = load_chat_ids()
    for chat_id in chat_ids:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=10
        )

# ===== FLASK APP =====
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True) or {}
    msg = data.get("message")
    if not msg: return "ok", 200
    text = msg.get("text", "").strip()
    chat_id = msg["chat"]["id"]
    if text == "/start":
        chat_ids = load_chat_ids()
        if str(chat_id) not in chat_ids:
            chat_ids.add(str(chat_id))
            save_chat_ids(chat_ids)
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": "Вас додано до сповіщень!"}
        )
    return "ok", 200

@app.route("/check", methods=["GET"])
def check_status():
    online = get_device_online()
    current = "є ✅" if online else "нема ❌"
    prev = load_state()

    if prev != current:
        send_telegram(f"Світло {current}!")
        save_state(current)

    return {"status": current, "changed": prev != current}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
