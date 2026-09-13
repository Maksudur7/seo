"""
Real Social Media Scraper — Dedicated Meta Threads Engine
=========================================================
1. Uses persistent Threads browser login session
2. Google Custom Search fallback (threads.net)
"""

import time
import requests
from config import load_config
from modules.platform_posters import load_history, save_history
from modules.ai_engine import AIEngine
from modules.telegram_notifier import send_telegram_alert
from modules.human_behavior import human


def fetch_via_google_cse(keyword, api_key, cx, site_filter="threads.net", limit=5):
    """Search real public Threads posts via Google Custom Search API."""
    if not api_key or not cx:
        return []
    query = f"site:{site_filter} {keyword}"
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": query, "num": min(limit, 10)}
    try:
        human.before_request("threads", "google_cse")
        resp = requests.get(url, params=params, timeout=12)
        if resp.status_code == 200:
            return [
                {
                    "platform": "Threads",
                    "title": item.get("title", ""),
                    "url": item.get("link", "#"),
                    "snippet": item.get("snippet", ""),
                    "keyword": keyword,
                    "reddit_id": None,
                }
                for item in resp.json().get("items", [])
            ]
    except Exception as e:
        print(f"[GoogleCSE] Threads error: {e}")
    return []


def fetch_threads_posts(keyword, api_key="", cx="", limit=5):
    """Fetch real Threads posts using logged-in browser session or CSE."""
    from modules.browser_login import browser_mgr
    browser_leads = browser_mgr.scrape_leads("threads", keyword, limit=limit)
    if browser_leads:
        return browser_leads
    if api_key and cx:
        raw_items = fetch_via_google_cse(keyword, api_key, cx, "threads.net", limit=limit * 2)
        exact_leads = []
        for item in raw_items:
            link = item.get("url", "")
            if "threads.net" in link:
                exact_leads.append(item)
                if len(exact_leads) >= limit:
                    break
        if exact_leads:
            return exact_leads
    return []


class RealLeadFetcher:
    """
    Orchestrates fetching real Meta Threads leads + auto-commenting.
    """

    def __init__(self, config=None):
        self.config = config or load_config()
        self.ai = AIEngine(self.config.get("gemini_api_key"))
        self.keywords = self.config.get("keywords", ["convert pdf", "pdf to word", "file converter", "compress pdf"])
        self.google_api_key = self.config.get("google_search_api_key", "").strip()
        self.google_cx = self.config.get("google_search_cx", "").strip()
        self.target_url = self.config.get("target_website_url", "").rstrip("/")

    def fetch_all(self, max_per_keyword=5):
        all_raw = []
        history = load_history()
        seen_ids = {item.get("id") for item in history}

        for keyword in self.keywords[:5]:
            threads_posts = fetch_threads_posts(keyword, self.google_api_key, self.google_cx, limit=max_per_keyword)
            all_raw.extend(threads_posts)
            human.short_pause(f"keyword-gap [{keyword}]")

        new_leads = []
        auto_replied = 0

        for post in all_raw:
            url = post.get("url", "")
            if not url or "threads.net" not in url:
                continue

            post_id = f"threads_real_{abs(hash(url)) % (10 ** 9)}"
            if post_id in seen_ids:
                continue
            seen_ids.add(post_id)

            post_text = f"{post.get('title', '')}\n{post.get('snippet', '')}"
            if not post_text.strip():
                continue

            intent = f"Needs {post.get('keyword', 'file converter')} tool"
            matched_url = self.target_url
            reply_text = f"You can use this free online tool: {self.target_url}"
            is_relevant = True

            if self.ai.api_key and self.ai.api_key.startswith("AIzaSy"):
                try:
                    ai_res = self.ai.analyze_and_draft_reply(post_text, platform="Threads")
                    if ai_res:
                        if ai_res.get("error"):
                            pass
                        elif not ai_res.get("is_relevant", True):
                            is_relevant = False
                        else:
                            intent = ai_res.get("intent_summary", intent)
                            matched_url = ai_res.get("matched_url", matched_url)
                            reply_text = ai_res.get("reply_text", reply_text)
                except Exception as e:
                    print(f"[AI] Error: {e}")

            if not is_relevant:
                continue

            # Auto-comment via browser on Threads
            posted_status = "lead_captured_ready_to_reply"
            if url:
                from modules.browser_login import browser_mgr
                ok, msg = browser_mgr.post_reply("threads", url, reply_text)
                if ok:
                    posted_status = "posted_automatically"
                    auto_replied += 1
                    print(f"[Threads Auto-Comment] ✅ Commented via browser on: {post['title'][:50]}")

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

        return {
            "status": "success",
            "count": len(new_leads),
            "leads": new_leads,
            "total_raw_scanned": len(all_raw),
            "threads_auto_commented": auto_replied,
        }
