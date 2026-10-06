"""
Run this once to get your initial OAuth2 tokens.
It opens a browser for you to authorize, then saves tokens to tokens.json.

Usage:
    HC_CLIENT_ID=xxx HC_CLIENT_SECRET=yyy python3 authorize.py
"""

import os
import json
import secrets
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

CLIENT_ID = os.environ["HC_CLIENT_ID"]
CLIENT_SECRET = os.environ["HC_CLIENT_SECRET"]
REDIRECT_URI = "http://localhost:8082/callback"
BASE_URL = "https://api.home-connect.com"
TOKEN_FILE = "tokens.json"

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = parse_qs(urlparse(self.path).query)
        auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Authorized! You can close this tab.</h2>")

    def log_message(self, *args):
        pass  # Suppress request logs


def authorize():
    state = secrets.token_urlsafe(16)
    auth_url = (
        f"{BASE_URL}/security/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=IdentifyAppliance%20Dishwasher"
        f"&state={state}"
    )

    print(f"\nOpening browser for Home Connect authorization...")
    print(f"If it doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8082), CallbackHandler)
    print("Waiting for authorization callback...")
    server.handle_request()

    if not auth_code:
        print("No auth code received. Exiting.")
        return

    # Exchange code for tokens
    resp = requests.post(f"{BASE_URL}/security/oauth/token", data={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": auth_code,
    })
    resp.raise_for_status()
    tokens = resp.json()

    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

    print(f"Tokens saved to {TOKEN_FILE}")

    # Print available appliances
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    appliances = requests.get(
        f"{BASE_URL}/api/homeappliances",
        headers=headers
    ).json()

    print("\nYour appliances:")
    for a in appliances.get("data", {}).get("homeappliances", []):
        print(f"  {a['name']} — haId: {a['haId']}")

    print("\nSet HC_APPLIANCE_HA_ID to your dishwasher's haId above.")


if __name__ == "__main__":
    authorize()
