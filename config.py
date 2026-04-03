# -----------------------------------------------------------------------
# config.py
# Get api_id and api_hash for each account at: https://my.telegram.org
# Log in, go to "API development tools", create an app per account.
# -----------------------------------------------------------------------

ACCOUNTS = [
    {
        "name": "Account 1",
        "api_id": 0,
        "api_hash": "",
        "phone": "+1234567890",
        "session_name": "sessions/account1",
    },
    {
        "name": "Account 2",
        "api_id": 0,
        "api_hash": "",
        "phone": "+0987654321",
        "session_name": "sessions/account2",
    },
    {
        "name": "Account 3",
        "api_id": 0,
        "api_hash": "",
        "phone": "+1122334455",
        "session_name": "sessions/account3",
    },
]

LOG_FILE = "responses.log"
HOST = "127.0.0.1"
PORT = 5000
