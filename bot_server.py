import os
import json
import requests
from flask import Flask, request

BOT_TOKEN = os.environ["BOT_TOKEN"]
USERS_FILE = "users.txt"

app = Flask(__name__)

def add_chat_id(chat_id):
    if not os.path.exists(USERS_FILE):
        users = set()
    else:
        with open(USERS_FILE, "r") as f:
            users = set(f.read().splitlines())
    users.add(str(chat_id))
    with open(USERS_FILE, "w") as f:
        f.write("\n".join(users))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]
        if text == "/start":
            add_chat_id(chat_id)
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
