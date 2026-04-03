"""
main.py -- Tournament C2 backend
Runs Telethon clients in a background asyncio loop alongside a Flask/SocketIO
server. The two halves communicate via run_coroutine_threadsafe and a
thread-safe shared state dict.
"""

import asyncio
import json
import logging
import os
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import Channel, Chat

import config

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "tournament_c2_key"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
state: dict = {
    "clients": {},    # account_name  -> TelegramClient
    "groups": {},     # account_name  -> [{id, name}]
    "forwards": {},   # forward_id    -> forward record
    "responses": [],  # flat list of all received replies
    "ready": False,
    "errors": [],     # any init errors
}
state_lock = threading.Lock()

# Background event loop that owns the Telethon clients
bg_loop = asyncio.new_event_loop()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log_response(entry: dict) -> None:
    """Append a JSON line to the flat log file."""
    with open(config.LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def make_forward_id() -> str:
    return f"fwd_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


# ---------------------------------------------------------------------------
# Telethon initialisation (runs inside bg_loop)
# ---------------------------------------------------------------------------

async def init_clients() -> None:
    os.makedirs("sessions", exist_ok=True)

    for acc in config.ACCOUNTS:
        try:
            client = TelegramClient(
                acc["session_name"],
                acc["api_id"],
                acc["api_hash"],
            )
            # start() will prompt for the OTP in the terminal on first run,
            # then save the session file so subsequent starts are silent.
            await client.start(phone=acc["phone"])
            logger.info("Authenticated: %s", acc["name"])

            # Build group list for the compose UI
            groups = []
            async for dialog in client.iter_dialogs():
                entity = dialog.entity
                if isinstance(entity, (Channel, Chat)):
                    groups.append({
                        "id": str(dialog.id),
                        "name": dialog.name or f"[{dialog.id}]",
                    })

            # Register reply listener
            @client.on(events.NewMessage(incoming=True))
            async def handle_incoming(event, acc_name=acc["name"]):
                if not event.is_reply:
                    return

                with state_lock:
                    for fwd_id, fwd_data in state["forwards"].items():
                        for dest in fwd_data["destinations"]:
                            if (
                                dest.get("sent_message_id") == event.reply_to_msg_id
                                and str(dest.get("chat_id")) == str(event.chat_id)
                            ):
                                try:
                                    sender = await event.get_sender()
                                    sender_name = (
                                        getattr(sender, "username", None)
                                        or getattr(sender, "first_name", None)
                                        or str(event.sender_id)
                                    )
                                except Exception:
                                    sender_name = str(event.sender_id)

                                entry = {
                                    "forward_id": fwd_id,
                                    "group_name": dest["group_name"],
                                    "group_id": str(dest["chat_id"]),
                                    "sender": sender_name,
                                    "text": event.raw_text,
                                    "timestamp": datetime.now().isoformat(),
                                    "account": acc_name,
                                }
                                state["responses"].append(entry)
                                log_response(entry)
                                # Push to dashboard via SocketIO
                                socketio.emit("new_response", entry)
                                logger.info(
                                    "Reply in %s from %s",
                                    dest["group_name"],
                                    sender_name,
                                )
                                break

            with state_lock:
                state["clients"][acc["name"]] = client
                state["groups"][acc["name"]] = sorted(
                    groups, key=lambda g: g["name"].lower()
                )

        except Exception as exc:
            logger.error("Failed to init %s: %s", acc["name"], exc)
            with state_lock:
                state["errors"].append({"account": acc["name"], "error": str(exc)})

    with state_lock:
        state["ready"] = True
        ready_accounts = list(state["clients"].keys())

    logger.info("Ready. Active accounts: %s", ready_accounts)
    socketio.emit("status_update", {"ready": True, "accounts": ready_accounts})

    # Keep all clients running
    active_clients = list(state["clients"].values())
    if active_clients:
        await asyncio.gather(
            *[c.run_until_disconnected() for c in active_clients]
        )


# ---------------------------------------------------------------------------
# Forward coroutine (runs inside bg_loop, called from Flask thread)
# ---------------------------------------------------------------------------

async def do_forward(account_name: str, message: str, destinations: list) -> tuple:
    """Send message from one account to N groups. Returns (fwd_id, results)."""
    client = state["clients"].get(account_name)
    if not client:
        return None, [{"error": f"Account '{account_name}' not connected"}]

    fwd_id = make_forward_id()
    dest_results = []

    for dest in destinations:
        try:
            peer_id = int(dest["id"])
            sent = await client.send_message(peer_id, message)
            dest_results.append({
                "chat_id": str(peer_id),
                "group_name": dest["name"],
                "sent_message_id": sent.id,
                "status": "sent",
            })
            logger.info("Forwarded to %s via %s", dest["name"], account_name)
        except FloodWaitError as exc:
            dest_results.append({
                "chat_id": str(dest["id"]),
                "group_name": dest["name"],
                "sent_message_id": None,
                "status": f"flood_wait:{exc.seconds}s",
            })
            logger.warning("Flood wait %ds for %s", exc.seconds, dest["name"])
        except Exception as exc:
            dest_results.append({
                "chat_id": str(dest["id"]),
                "group_name": dest["name"],
                "sent_message_id": None,
                "status": f"error:{exc}",
            })
            logger.error("Failed to send to %s: %s", dest["name"], exc)

    with state_lock:
        state["forwards"][fwd_id] = {
            "id": fwd_id,
            "message": message,
            "account": account_name,
            "timestamp": datetime.now().isoformat(),
            "destinations": dest_results,
        }

    socketio.emit("forward_created", state["forwards"][fwd_id])
    return fwd_id, dest_results


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/status")
def api_status():
    with state_lock:
        return jsonify({
            "ready": state["ready"],
            "accounts": list(state["clients"].keys()),
            "errors": state["errors"],
        })


@app.route("/api/accounts")
def api_accounts():
    with state_lock:
        return jsonify(list(state["clients"].keys()))


@app.route("/api/groups/<path:account_name>")
def api_groups(account_name):
    with state_lock:
        groups = state["groups"].get(account_name, [])
    return jsonify(groups)


@app.route("/api/forward", methods=["POST"])
def api_forward():
    data = request.json or {}
    account_name = data.get("account", "").strip()
    message = data.get("message", "").strip()
    destinations = data.get("destinations", [])

    if not account_name or not message or not destinations:
        return jsonify({"error": "account, message, and destinations are required"}), 400

    future = asyncio.run_coroutine_threadsafe(
        do_forward(account_name, message, destinations),
        bg_loop,
    )
    try:
        fwd_id, results = future.result(timeout=30)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"forward_id": fwd_id, "results": results})


@app.route("/api/forwards")
def api_forwards():
    with state_lock:
        return jsonify(list(state["forwards"].values()))


@app.route("/api/responses")
def api_responses():
    fwd_id = request.args.get("forward_id")
    with state_lock:
        responses = list(state["responses"])
    if fwd_id:
        responses = [r for r in responses if r["forward_id"] == fwd_id]
    return jsonify(responses)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    def run_background_loop():
        asyncio.set_event_loop(bg_loop)
        bg_loop.run_until_complete(init_clients())

    bg_thread = threading.Thread(target=run_background_loop, daemon=True)
    bg_thread.start()

    logger.info("Dashboard at http://%s:%s", config.HOST, config.PORT)
    socketio.run(app, host=config.HOST, port=config.PORT, debug=False)
