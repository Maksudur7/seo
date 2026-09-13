"""
Threads Platform Listener & Auto-Reply Module
Uses Meta's official Threads API (free) to:
1. Search/monitor mentions and hashtag posts
2. Auto-reply to relevant posts with website link

How to get Threads API credentials (FREE):
1. Go to developers.facebook.com
2. Create an App -> Add "Threads" product
3. Get Threads User ID and Access Token
4. Add them in Dashboard -> Settings
"""

import time
import requests
from config import load_config
from modules.platform_posters import load_history, save_history
from modules.ai_engine import AIEngine
from modules.telegram_notifier import send_telegram_alert
from modules.human_behavior import human


class ThreadsListener:
    BASE_URL = "https://graph.threads.net/v1.0"

    def __init__(self, config=None):
        self.config = config or load_config()
        self.threads_cfg = self.config.get("threads", {})
        self.access_token = self.threads_cfg.get("access_token", "").strip()
        self.user_id = self.threads_cfg.get("user_id", "").strip()
        self.ai = AIEngine(self.config.get("gemini_api_key"))
        self.keywords = self.config.get("keywords", ["convert pdf", "file converter"])
        self.target_url = self.config.get("target_website_url", "").rstrip("/")

    def is_configured(self):
        return bool(self.access_token and self.user_id)

    def get_user_threads(self, limit=10):
        """Fetch recent threads from your own Threads account."""
        if not self.is_configured():
            return []
        url = f"{self.BASE_URL}/{self.user_id}/threads"
        params = {
            "fields": "id,text,timestamp,permalink",
            "access_token": self.access_token,
            "limit": limit
        }
        try:
            human.before_request("threads", "get-user-threads")
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code == 200:
                return resp.json().get("data", [])
        except Exception as e:
            print(f"[Threads] Get threads error: {e}")
        return []

    def search_threads_keyword(self, keyword, limit=5):
        """
        Search public Threads posts by keyword.
        Note: Threads API currently supports searching via the /threads endpoint with q parameter.
        """
        if not self.is_configured():
            return []
        url = f"{self.BASE_URL}/threads"
        params = {
            "q": keyword,
            "fields": "id,text,timestamp,permalink,username",
            "access_token": self.access_token,
            "limit": limit
        }
        try:
            human.before_request("threads", "search")
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code == 200:
                posts = resp.json().get("data", [])
                return [
                    {
                        "platform": "Threads",
                        "title": p.get("text", "")[:200],
                        "url": p.get("permalink", "#"),
                        "snippet": p.get("text", "")[:300],
                        "keyword": keyword,
                        "threads_post_id": p.get("id"),
                    }
                    for p in posts if p.get("text")
                ]
            else:
                print(f"[Threads Search] HTTP {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"[Threads Search] Error: {e}")
        return []

    def post_reply(self, post_id, reply_text):
        """
        Post a reply to a Threads post using the Threads API.
        Step 1: Create reply container
        Step 2: Publish the container
        Returns: (success: bool, status_message: str)
        """
        if not self.is_configured():
            return False, "threads_not_configured"

        try:
            # Step 1: Create a reply media container
            create_url = f"{self.BASE_URL}/{self.user_id}/threads"
            create_data = {
                "media_type": "TEXT",
                "text": reply_text,
                "reply_to_id": post_id,
                "access_token": self.access_token,
            }
            human.before_request("threads", "create-container")
            create_resp = requests.post(create_url, data=create_data, timeout=12)
            if create_resp.status_code != 200:
                err = create_resp.json().get("error", {}).get("message", "Unknown error")
                return False, f"create_failed_{err[:40]}"

            container_id = create_resp.json().get("id")
            if not container_id:
                return False, "no_container_id"

            # Step 2: Publish the container
            # Human-like: brief pause before publishing (review the draft)
            human.jitter_delay("threads-pre-publish")
            publish_url = f"{self.BASE_URL}/{self.user_id}/threads_publish"
            publish_data = {
                "creation_id": container_id,
                "access_token": self.access_token,
            }
            human.before_request("threads", "publish")
            publish_resp = requests.post(publish_url, data=publish_data, timeout=12)
            if publish_resp.status_code == 200:
                return True, "posted_automatically"
            else:
                err = publish_resp.json().get("error", {}).get("message", "Unknown")
                return False, f"publish_failed_{err[:40]}"

        except Exception as e:
            print(f"[Threads Reply] Error: {e}")
            return False, f"exception_{str(e)[:40]}"

    def run_scan(self):
        """
        Main scan: search Threads for keywords, AI-analyze, auto-reply.
        """
        if not self.is_configured():
            return {"status": "skipped", "message": "Threads access_token or user_id not set."}

        history = load_history()
        seen_ids = {item.get("id") for item in history}
        new_leads = []
        auto_replied = 0

        for keyword in self.keywords[:5]:  # Limit keywords per cycle
            posts = self.search_threads_keyword(keyword, limit=5)
            for post in posts:
                post_id = f"threads_{post.get('threads_post_id', abs(hash(post['url'])) % (10**9))}"
                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                post_text = f"{post.get('title', '')}\n{post.get('snippet', '')}"
                if not post_text.strip():
                    continue

                intent = f"Needs {keyword} tool"
                matched_url = self.target_url
                reply_text = f"You can use this free online tool: {self.target_url}"
                is_relevant = True

                if self.ai.api_key and self.ai.api_key.startswith("AIzaSy"):
                    try:
                        ai_res = self.ai.analyze_and_draft_reply(post_text, platform="Threads")
                        if ai_res and not ai_res.get("error"):
                            if not ai_res.get("is_relevant", True):
                                is_relevant = False
                            else:
                                intent = ai_res.get("intent_summary", intent)
                                matched_url = ai_res.get("matched_url", matched_url)
                                reply_text = ai_res.get("reply_text", reply_text)
                    except Exception as e:
                        print(f"[Threads AI] Error: {e}")

                if not is_relevant:
                    continue

                # Auto-reply
                posted_status = "lead_captured_ready_to_reply"
                threads_post_id = post.get("threads_post_id")
                if threads_post_id:
                    # Check daily budget before acting
                    if not human.can_act("threads"):
                        posted_status = "skipped_daily_budget_exceeded"
                    else:
                        # Read the post before replying
                        human.read_pause("threads-before-reply")
                        # Humanize reply text
                        humanized_reply = human.humanize_reply(reply_text, platform="Threads")
                        # Simulate typing
                        human.simulate_typing(humanized_reply, "threads-reply")
                        success, msg = self.post_reply(threads_post_id, humanized_reply)
                        if success:
                            posted_status = "posted_automatically"
                            auto_replied += 1
                            human.record_action("threads")
                            print(f"[Threads Auto-Reply] OK: {post['title'][:60]}")
                            # Post-action pause + fatigue check
                            human.after_post_pause("threads-post-reply")
                            human.session_fatigue_check("threads")
                        else:
                            posted_status = f"threads_reply_failed_{msg}"
                            print(f"[Threads Auto-Reply] Failed ({msg}): {post['title'][:60]}")
                            human.short_pause("threads-failed-retry-gap")

                record = {
                    "id": post_id,
                    "platform": "Threads",
                    "title": post["title"][:150],
                    "url": post["url"],
                    "intent": intent,
                    "matched_url": matched_url,
                    "reply_text": reply_text,
                    "status": posted_status,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                save_history(record)
                send_telegram_alert(record)
                new_leads.append(record)

            # Human pause between keyword searches
            human.short_pause("threads-keyword-gap")

        return {
            "status": "success",
            "leads_found": len(new_leads),
            "auto_replied": auto_replied,
            "leads": new_leads,
        }
