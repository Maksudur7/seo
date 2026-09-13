"""
Telegram Callback Bot Handler
- Receives button press callbacks from Telegram
- Uses long-polling (works on localhost - no public URL needed!)
- When user clicks "Post Now" button -> posts comment to the platform automatically
- Supports: Reddit, Threads, Twitter/X, Stack Overflow
- For Facebook/Instagram: sends direct link to open
"""

import time
import threading
import requests
from config import load_config
from modules.platform_posters import load_history, save_history


# ─────────────────────────────────────────────────────────────────
# Telegram API Helpers
# ─────────────────────────────────────────────────────────────────

def get_updates(bot_token, offset=None, timeout=30):
    """Long-poll Telegram for new updates (button clicks)."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {"timeout": timeout, "allowed_updates": ["callback_query"]}
    if offset:
        params["offset"] = offset
    try:
        resp = requests.get(url, params=params, timeout=timeout + 5)
        if resp.status_code == 200:
            return resp.json().get("result", [])
    except Exception as e:
        print(f"[TelegramCallback] getUpdates error: {e}")
    return []


def answer_callback(bot_token, callback_query_id, text, show_alert=False):
    """Answer a callback query (removes the loading spinner on button)."""
    url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
    requests.post(url, json={
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert
    }, timeout=10)


def edit_message_text(bot_token, chat_id, message_id, new_text):
    """Edit the original Telegram message after action."""
    url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
    requests.post(url, json={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": new_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }, timeout=10)


# ─────────────────────────────────────────────────────────────────
# Platform Posting Actions
# ─────────────────────────────────────────────────────────────────

def execute_post_for_lead(lead_id: str) -> tuple:
    """
    Find the lead by ID and post comment to the platform.
    Returns: (success: bool, message: str)
    """
    config = load_config()
    history = load_history()
    lead = next((l for l in history if l.get("id") == lead_id), None)

    if not lead:
        return False, "Lead not found in history"

    platform = lead.get("platform", "")
    reply_text = lead.get("reply_text", "")
    lead_url = lead.get("url", "#")

    if not reply_text:
        return False, "No reply text available"

    # ── Reddit ──────────────────────────────────────────────
    if "Reddit" in platform:
        reddit_cfg = config.get("reddit", {})
        # Extract Reddit submission ID from URL
        # URL format: https://reddit.com/r/subreddit/comments/SUBMISSION_ID/...
        reddit_id = None
        url_parts = lead_url.rstrip("/").split("/")
        try:
            comments_idx = url_parts.index("comments")
            reddit_id = url_parts[comments_idx + 1]
        except (ValueError, IndexError):
            pass

        if not reddit_id:
            # Try from lead ID: real_XXXXXXXXX -> no reddit ID stored
            return False, "Could not extract Reddit submission ID from URL"

        try:
            import praw
            client_id = reddit_cfg.get("client_id", "").strip()
            client_secret = reddit_cfg.get("client_secret", "").strip()
            username = reddit_cfg.get("username", "").strip()
            password = reddit_cfg.get("password", "").strip()

            if not all([client_id, client_secret, username, password]):
                return False, "Reddit credentials not configured in Settings"

            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=reddit_cfg.get("user_agent", "SEOBot/2.0"),
                username=username,
                password=password,
            )
            submission = reddit.submission(id=reddit_id)
            submission.reply(reply_text)
            return True, f"✅ Comment posted on Reddit successfully!"
        except Exception as e:
            err = str(e)
            if "RATELIMIT" in err.upper():
                return False, "Reddit rate limited - try after some time"
            return False, f"Reddit error: {err[:60]}"

    # ── Meta Threads ─────────────────────────────────────────
    from modules.threads_listener import ThreadsListener
    listener = ThreadsListener(config)
    if listener.is_configured():
        threads_post_id = lead_id.replace("threads_", "").replace("real_", "") if lead_id.startswith("threads_") else None
        if threads_post_id:
            success, msg = listener.post_reply(threads_post_id, reply_text)
            if success:
                return True, "✅ Reply posted on Threads API successfully!"

    # Fallback: Threads Browser Session Posting
    from modules.browser_login import browser_mgr
    ok, msg = browser_mgr.post_reply("threads", lead_url, reply_text)
    if ok:
        return True, "✅ Reply posted on Threads Browser successfully!"
    return False, f"Threads posting status: {msg}"



def update_lead_status(lead_id: str, new_status: str):
    """Update lead status in history after posting."""
    history = load_history()
    for lead in history:
        if lead.get("id") == lead_id:
            lead["status"] = new_status
            lead["posted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            break
    from modules.platform_posters import HISTORY_FILE
    import json
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────
# Callback Dispatcher
# ─────────────────────────────────────────────────────────────────

def handle_callback(update: dict, bot_token: str):
    """
    Process a single Telegram callback query (button click).
    callback_data format:
      "post_LEAD_ID"  -> post comment to platform
      "skip_LEAD_ID"  -> mark as skipped
    """
    cq = update.get("callback_query", {})
    callback_id = cq.get("id")
    data = cq.get("data", "")
    chat_id = cq.get("message", {}).get("chat", {}).get("id")
    message_id = cq.get("message", {}).get("message_id")

    if not data or not callback_id:
        return

    parts = data.split("_", 1)
    action = parts[0] if parts else ""
    lead_id = parts[1] if len(parts) > 1 else ""

    if action == "post":
        # Immediately acknowledge the button press
        answer_callback(bot_token, callback_id, "⏳ Posting...", show_alert=False)

        # Execute the post
        success, result_msg = execute_post_for_lead(lead_id)

        if success:
            new_status = "posted_via_telegram"
            update_lead_status(lead_id, new_status)
            answer_callback(bot_token, callback_id, result_msg, show_alert=True)
            # Edit original message to show posted status
            edit_message_text(
                bot_token, chat_id, message_id,
                f"✅ <b>POSTED!</b>\n{result_msg}\n\n<i>Lead ID: {lead_id[:20]}...</i>"
            )
        else:
            answer_callback(bot_token, callback_id, f"❌ {result_msg}", show_alert=True)

    elif action == "skip":
        update_lead_status(lead_id, "skipped_via_telegram")
        answer_callback(bot_token, callback_id, "⏭️ Lead skipped", show_alert=False)
        edit_message_text(
            bot_token, chat_id, message_id,
            f"⏭️ <b>Skipped</b>\n<i>Lead ID: {lead_id[:20]}...</i>"
        )


# ─────────────────────────────────────────────────────────────────
# Background Long-Poll Thread
# ─────────────────────────────────────────────────────────────────

class TelegramCallbackHandler:
    """
    Background thread that listens for Telegram button clicks
    using long-polling. No public URL or webhook setup needed!
    Works perfectly on localhost.
    """

    def __init__(self):
        self._running = False
        self._thread = None
        self._offset = None

    def start(self):
        config = load_config()
        bot_token = config.get("telegram", {}).get("bot_token", "").strip()
        if not bot_token:
            print("[TelegramCallback] No bot token configured, callback handler not started.")
            return
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
            print("[TelegramCallback] Callback handler started (long-polling).")

    def stop(self):
        self._running = False
        print("[TelegramCallback] Callback handler stopped.")

    def _poll_loop(self):
        while self._running:
            try:
                config = load_config()
                bot_token = config.get("telegram", {}).get("bot_token", "").strip()
                if not bot_token:
                    time.sleep(30)
                    continue

                updates = get_updates(bot_token, offset=self._offset, timeout=25)
                for update in updates:
                    update_id = update.get("update_id")
                    if update_id:
                        self._offset = update_id + 1

                    if "callback_query" in update:
                        try:
                            handle_callback(update, bot_token)
                        except Exception as e:
                            print(f"[TelegramCallback] Handler error: {e}")

            except Exception as e:
                print(f"[TelegramCallback] Poll loop error: {e}")
                time.sleep(5)


# Global instance
telegram_callback_handler = TelegramCallbackHandler()
