"""
Telegram Notifier - sends lead alerts with inline keyboard buttons.
User can click "✅ Post এখনই" to auto-post to the platform from Telegram.
"""

import requests
from config import load_config

# Platform icons
PLATFORM_ICONS = {
    "Reddit": "🟠",
    "Stack Overflow": "📚",
    "Twitter": "🐦",
    "Twitter/X": "🐦",
    "Threads": "🧵",
    "Facebook": "🔵",
    "Instagram": "📸",
    "Quora": "🔴",
}

# Platforms that support auto-posting via button
AUTO_POST_PLATFORMS = {"Reddit", "Threads", "Twitter/X", "Stack Overflow", "Facebook", "Instagram"}


def send_telegram_alert(lead_data: dict):
    """
    Send a lead notification to Telegram with inline keyboard buttons.
    
    Buttons:
    - "✅ Post এখনই" (for Reddit/Threads/Twitter/SO) -> triggers auto-post
    - "🔗 Post খুলুন" (for Facebook/Instagram) -> opens post link
    - "⏭️ Skip" -> marks as skipped
    """
    config = load_config()
    telegram_cfg = config.get("telegram", {})
    bot_token = telegram_cfg.get("bot_token", "").strip()
    chat_id = telegram_cfg.get("chat_id", "").strip()

    if not bot_token or not chat_id:
        return False

    platform = lead_data.get("platform", "Social Media")
    lead_id = lead_data.get("id", "")
    title = lead_data.get("title", "New Lead")[:100]
    post_url = lead_data.get("url", "#")
    matched_url = lead_data.get("matched_url", "")
    reply_text = lead_data.get("reply_text", "")
    status = lead_data.get("status", "drafted")
    intent = lead_data.get("intent", "")
    timestamp = lead_data.get("timestamp", "")

    # Platform icon
    p_icon = "📌"
    for key, icon in PLATFORM_ICONS.items():
        if key in platform:
            p_icon = icon
            break

    # Already auto-posted?
    is_auto_posted = status in ["posted_automatically", "posted_automatically_via_browser"]

    if is_auto_posted:
        status_line = "🎉 <b>অটো-কমেন্ট পোস্ট সম্পন্ন হয়েছে!</b> (সিস্টেম সরাসরি ব্রাউজারে কমেন্ট পোস্ট করে দিয়েছে)"
    else:
        status_line = "📝 <b>নতুন লিড সংগৃহীত</b> — নিচে ক্লিক করে কমেন্ট পোস্ট করুন"

    # Message text (AI reply in <code></code> for 1-tap copy in Telegram!)
    message = (
        f"🚀 <b>New Lead Notification</b> {p_icon} {platform}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 <b>Post Heading:</b> {title}\n"
        f"🔗 <b>Post Link:</b> <a href=\"{post_url}\">{post_url}</a>\n"
        f"🎯 <b>Intent:</b> {intent}\n"
        f"⏰ <b>Time:</b> {timestamp}\n"
        f"\n"
        f"💬 <b>AI Posted Comment</b> 📋:\n"
        f"<code>{reply_text}</code>\n"
        f"\n"
        f"🌐 <b>Website Link:</b> <a href=\"{matched_url}\">{matched_url}</a>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{status_line}"
    )

    # Build inline keyboard
    keyboard_rows = []

    if is_auto_posted:
        # Direct link button to the post where comment was submitted
        if post_url and post_url != "#":
            keyboard_rows.append([
                {"text": "👁️ কমেন্ট করা Post টি খুলুন 🔗", "url": post_url}
            ])
            keyboard_rows.append([
                {"text": "🌐 Visit mr-converter.com", "url": "https://mr-converter.com"}
            ])
    else:
        # Check if this platform supports 1-click auto-posting
        can_auto_post = any(p in platform for p in AUTO_POST_PLATFORMS)

        if can_auto_post and lead_id:
            keyboard_rows.append([
                {"text": "✅ এখনই Post করো", "callback_data": f"post_{lead_id}"},
                {"text": "⏭️ Skip", "callback_data": f"skip_{lead_id}"}
            ])
        else:
            keyboard_rows.append([
                {"text": "🔗 Post খুলুন", "url": post_url},
                {"text": "⏭️ Skip", "callback_data": f"skip_{lead_id}" if lead_id else "skip_none"}
            ])
        if post_url and post_url != "#":
            keyboard_rows.append([
                {"text": "👁️ Post দেখুন", "url": post_url}
            ])

    reply_markup = {"inline_keyboard": keyboard_rows} if keyboard_rows else None

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        res = requests.post(api_url, json=payload, timeout=12)
        if res.status_code == 200:
            print(f"[Telegram] Alert sent for {platform} with buttons")
            return True
        else:
            print(f"[Telegram] Error {res.status_code}: {res.text[:80]}")
            return False
    except Exception as e:
        print(f"[Telegram] Send failed: {e}")
        return False


def send_simple_message(text: str):
    """Send a plain text message to Telegram (for system notifications)."""
    config = load_config()
    telegram_cfg = config.get("telegram", {})
    bot_token = telegram_cfg.get("bot_token", "").strip()
    chat_id = telegram_cfg.get("chat_id", "").strip()
    if not bot_token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
        return True
    except Exception:
        return False
