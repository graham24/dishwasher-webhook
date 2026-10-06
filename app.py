from flask import Flask, jsonify
from datetime import datetime, timezone
import requests
import json
import os

app = Flask(__name__)

# --- Config ---
CLIENT_ID = os.environ["HC_CLIENT_ID"]
CLIENT_SECRET = os.environ["HC_CLIENT_SECRET"]
APPLIANCE_HA_ID = os.environ["HC_APPLIANCE_HA_ID"]
TOKEN_FILE = "tokens.json"

BASE_URL = "https://api.home-connect.com"


# --- Token Management ---

def load_tokens():
    with open(TOKEN_FILE) as f:
        return json.load(f)

def save_tokens(tokens):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)

def refresh_access_token():
    tokens = load_tokens()
    resp = requests.post(f"{BASE_URL}/security/oauth/token", data={
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": tokens["refresh_token"],
    })
    resp.raise_for_status()
    new_tokens = resp.json()
    save_tokens(new_tokens)
    return new_tokens["access_token"]

def get_access_token():
    tokens = load_tokens()
    # Try existing token; if it fails, refresh
    return tokens.get("access_token")


def api_headers():
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }


def api_request(method, path, **kwargs):
    """Make an API request, refreshing token once on 401."""
    url = f"{BASE_URL}{path}"
    resp = requests.request(method, url, headers=api_headers(), **kwargs)
    if resp.status_code == 401:
        # Token expired — refresh and retry once
        refresh_access_token()
        resp = requests.request(method, url, headers=api_headers(), **kwargs)
    resp.raise_for_status()
    return resp


# --- Delay Calculation ---

def seconds_until_1am():
    """Seconds from now until the next 1:00 AM local time."""
    now = datetime.now()
    target = now.replace(hour=1, minute=0, second=0, microsecond=0)
    if target <= now:
        # Already past 1am today — aim for tomorrow
        from datetime import timedelta
        target += timedelta(days=1)
    return int((target - now).total_seconds())


# --- Webhook Endpoint ---

@app.route("/dishwasher/start", methods=["POST"])
def start_dishwasher():
    delay = seconds_until_1am()

    program_key = "Dishcare.Dishwasher.Program.Auto2"  # Bosch Auto program

    payload = {
        "data": {
            "key": program_key,
            "options": [
                {
                    "key": "BSH.Common.Option.StartInRelative",
                    "value": delay,
                    "unit": "seconds"
                }
            ]
        }
    }

    path = f"/api/homeappliances/{APPLIANCE_HA_ID}/programs/active"

    try:
        api_request("PUT", path, json=payload)
    except requests.HTTPError as e:
        print(e)
        if e.response is not None:
            print(e.response.text)
        if e.response is not None and e.response.status_code == 409:
            error_key = e.response.json().get("error", {}).get("key", "")
            if error_key == "SDK.Error.ProgramNotWritable":
                return jsonify({
                    "status": "error",
                    "detail": "Remote start not enabled on dishwasher panel"
                }), 409
            # Another program is active — cancel it and retry
            try:
                api_request("DELETE", path)
                api_request("PUT", path, json=payload)
            except requests.HTTPError as retry_err:
                print(retry_err)
                return jsonify({
                    "status": "error",
                    "detail": retry_err.response.text if retry_err.response else None
                }), 500
        else:
            return jsonify({
                "status": "error",
                "detail": e.response.text if e.response else None
            }), 500

    hours, remainder = divmod(delay, 3600)
    minutes = remainder // 60

    return jsonify({
        "status": "scheduled",
        "program": "Auto",
        "starts_in": f"{hours}h {minutes}m",
        "starts_at": "01:00"
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
