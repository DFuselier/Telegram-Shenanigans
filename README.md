# Tournament C2

A dispatch console for forwarding tournament announcements from multiple personal
Telegram accounts to clan groups, with real-time response tracking.

---

## Setup

### 1. Get API credentials for each account

Each personal Telegram account needs its own API ID and hash:

1. Go to https://my.telegram.org and log in with the account's phone number
2. Click "API development tools"
3. Create an app (name/description don't matter)
4. Copy the `api_id` (integer) and `api_hash` (string)
5. Repeat for each of the 3 accounts

### 2. Fill in config.py

Open `config.py` and fill in `api_id`, `api_hash`, and `phone` for each account.
Phone numbers must include the country code (e.g. +1234567890).

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. First run (authentication)

On the very first run, Telethon will prompt for an OTP for each account in the
terminal. After entering them, session files are saved in the `sessions/` folder
and future startups are silent.

```bash
python main.py
```

Open http://127.0.0.1:5000 in your browser.

---

## Usage

1. Select which account to send from in the dropdown
2. Write your message
3. Check the groups you want to reach (loads dynamically per account)
4. Hit "Dispatch Message"

The Response Tracker panel updates in real time as clan members reply.
Every reply is also appended as a JSON line to `responses.log`.

---

## Files

```
tournament_c2/
  config.py              Account credentials and settings
  main.py                Flask + Telethon backend
  templates/
    dashboard.html       Web UI
  sessions/              Telethon session files (auto-created, do not delete)
  responses.log          Append-only log of all replies (auto-created)
  requirements.txt
```

---

## Notes

- The `sessions/` folder contains your login state. Back it up and do not share it.
- If an account triggers a flood wait, the UI will show the wait time on that
  destination and the message will need to be retried after the cooldown.
- Response scraping captures any reply to a dispatched message. There is no
  keyword filter -- any reply counts as a response.
- The dashboard is served locally only (127.0.0.1). Do not expose it to the
  internet without adding authentication.
