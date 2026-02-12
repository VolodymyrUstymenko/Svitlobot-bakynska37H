import os
import requests
import time
import hmac
import hashlib
from flask import Flask, request
import json
# ===== CONFIG =====
ACCESS_ID = os.environ["ACCESS_ID"]
ACCESS_SECRET = os.environ["ACCESS_SECRET"]
DEVICE_ID = os.environ["DEVICE_ID"]
REGION = os.environ.get("REGION", "eu")
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
GIST_ID = os.environ["GIST_ID"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
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
    return (data["result"]["online"], data["t"])

def load_state():
    url = f"https://api.github.com/gists/{GIST_ID}"
    r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    r.raise_for_status()
    data = r.json()
    content = data["files"]["bot_state.json"]["content"]
    return json.loads(content)

def save_state(state_dict):
    url = f"https://api.github.com/gists/{GIST_ID}"
    payload = {
        "files": {
            "bot_state.json": {
                "content": json.dumps(state_dict, indent=2)
            }
        }
    }
    r = requests.patch(url, json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    r.raise_for_status()
        
def send_telegram(msg):
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHANNEL_ID, "text": msg},
        timeout=10
    )
    print(r.status_code, r.text)

# ===== FLASK APP =====
app = Flask(__name__)

@app.route("/check", methods=["GET"])
def check_status():
    state = load_state()
    last_state = state.get("last_state", None)
    time = state.get("time", None)
    (online, t) = get_device_online()
    current_state = "online" if online else "offline"
    if current_state != last_state:
        word = '⏱ Відключення тривало' if online else '⏱ Світло було впродовж'
        msg = "Світло З'ЯВИЛОСЯ ✅" if online else "Світла ЗНИКЛО ❌"
        duration_hours = (time - t) // 3600000
        duration_minutes = ((time - t) % 3600000) // 60000
        text = msg + '\n' + word + f"{duration_hours} год {duration_minutes} хв"
        send_telegram(text)
        state["last_state"] = current_state
        state["time"] = t
        save_state(state)
    return {"status": current_state}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
