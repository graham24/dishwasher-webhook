# Bosch Dishwasher Webhook

Flask webhook to start your Bosch dishwasher's Auto program delayed to 1am.
Triggered from Apple Shortcuts via a simple HTTP POST.

---

## 1. Get a Home Connect Developer Account

1. Go to https://developer.home-connect.com and sign in with your Bosch/Home Connect account
2. Click **Applications → Register Application**
3. Fill in:
   - **Application ID**: anything (e.g. `dishwasher-webhook`)
   - **OAuth Flow**: Authorization Code Grant
   - **Redirect URI**: `http://localhost:8082/callback`
   - **Scope**: `IdentifyAppliance Dishwasher`
4. Save — you'll get a **Client ID** and **Client Secret**

---

## 2. Install & Authorize

```bash
pip install -r requirements.txt

HC_CLIENT_ID=your_client_id HC_CLIENT_SECRET=your_client_secret python3 authorize.py
```

This opens a browser, you log in with your Home Connect account, and it saves
`tokens.json` + prints your appliance `haId`.

---

## 3. Run the Server

```bash
HC_CLIENT_ID=your_client_id \
HC_CLIENT_SECRET=your_client_secret \
HC_APPLIANCE_HA_ID=your_ha_id \
python3 app.py
```

Server runs on port **5001**.

---

## 4. Apple Shortcut

1. Open Shortcuts → New Shortcut
2. Add action: **Get Contents of URL**
   - URL: `http://your-server-ip:5001/dishwasher/start`
   - Method: `POST`
3. That's it — run the shortcut anytime to queue the 1am start

---

## Notes

- The server calculates delay from *now* to the next 1:00 AM automatically
- Tokens refresh automatically when expired
- Make sure your dishwasher is loaded and the door is closed before triggering
- `tokens.json` contains your OAuth tokens — keep it private
