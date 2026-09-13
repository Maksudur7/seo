"""
BrowserSessionManager — Dedicated Meta Threads Browser Login & Scraping Engine
=============================================================================
Meta Threads এর জন্য persistent Chrome profile সংরক্ষণ করে।
একবার লগইন করলে session স্থায়ীভাবে থাকবে।

ব্যবহার:
  1. Login Mode (Visible):  open_login_window("threads")
     → Chrome window খুলবে → ইউজার নিজে লগইন করবেন → বন্ধ করবেন
  2. Scrape Mode (Hidden):  scrape_leads("threads", keyword)
     → Headless/Visible Chrome → Threads পোস্ট সার্চ ও শেয়ার লিংক এক্সট্র্যাক্ট করবে
  3. Post Mode (Hidden):    post_reply("threads", post_url, reply_text)
     → Threads পোস্টে automatic AI-comment পোস্ট করবে
"""

import asyncio
import json
import time
import random
import threading
import sys
from pathlib import Path
from typing import Optional

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────
# Platform config (Threads ONLY)
# ─────────────────────────────────────────────────────────────

PLATFORMS = {
    "threads": {
        "name":        "Meta Threads",
        "login_url":   "https://www.threads.net/login/",
        "home_url":    "https://www.threads.net/",
        "search_url":  "https://www.threads.net/search/?q={keyword}&sort=recent",
        "login_check": ["a[href='/']", "svg[aria-label='Home']", "a[href*='threads']", "[aria-label='Profile']"],
        "emoji":       "🧵",
    }
}

# ─────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────

BASE_DIR     = Path(__file__).resolve().parent.parent
PROFILES_DIR = BASE_DIR / "data" / "browser_profiles"
STATUS_FILE  = BASE_DIR / "data" / "browser_status.json"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# Playwright availability check
# ─────────────────────────────────────────────────────────────

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("[BrowserLogin] ⚠️  playwright not installed. Run: pip install playwright")

# System Chrome path (uses existing Chrome browser if present)
SYSTEM_CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def _get_browser_args():
    """Return Chrome executable path if system Chrome exists, else None."""
    import os
    return SYSTEM_CHROME if os.path.exists(SYSTEM_CHROME) else None


def _clean_profile_locks(profile_dir):
    """Remove stale Chrome SingletonLock files before launching browser context."""
    try:
        p = Path(profile_dir)
        for lock_name in ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]:
            lock_path = p / lock_name
            if lock_path.exists():
                try:
                    lock_path.unlink()
                except Exception:
                    pass
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# Human-like browser helpers
# ─────────────────────────────────────────────────────────────

def _human_delay(min_s=0.5, max_s=2.0):
    """Random pause simulating human reaction time."""
    time.sleep(random.uniform(min_s, max_s))


def _random_scroll(page, amount_min=200, amount_max=600):
    """Scroll page by a random human-like amount safely."""
    try:
        amount = random.randint(amount_min, amount_max)
        try:
            page.mouse.wheel(0, amount)
        except Exception:
            page.evaluate(f"window.scrollBy(0, {amount})")
        _human_delay(0.4, 1.0)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# Main Manager
# ─────────────────────────────────────────────────────────────

class BrowserSessionManager:
    """
    Manages persistent browser profiles exclusively for Meta Threads.
    Single instance shared across the app (imported as `browser_mgr`).
    """

    def __init__(self):
        self._status_cache = {}
        self._load_status()
        self._login_thread: Optional[threading.Thread] = None
        self._locks = {p: threading.Lock() for p in PLATFORMS}
        print("[BrowserLogin] ✅ Threads Browser Session Manager ready")

    def _is_logged_in(self, platform: str = "threads", context=None, page=None) -> bool:
        """Multi-stage verification to detect logged-in state on Threads."""
        try:
            if context:
                cookies = {c['name']: c['value'] for c in context.cookies()}
                if "sessionid" in cookies or "ds_user_id" in cookies:
                    return True

            if page:
                url = page.url.lower()
                if "login" not in url and "threads.net" in url:
                    for sel in ["svg[aria-label='Home']", "a[href='/']", "[aria-label='Profile']", "svg[aria-label='Create']"]:
                        if page.query_selector(sel):
                            return True
        except Exception as e:
            print(f"[BrowserLogin] Login check exception ({platform}): {e}")

        return False

    def open_login_window(self, platform: str = "threads") -> dict:
        """Opens a VISIBLE Chrome window for the user to log in to Threads."""
        if not HAS_PLAYWRIGHT:
            return {"status": "error", "message": "playwright not installed"}
        platform = "threads"

        self._login_thread = threading.Thread(
            target=self._run_login_window,
            args=(platform,),
            daemon=True
        )
        self._login_thread.start()

        cfg = PLATFORMS["threads"]
        return {
            "status": "opening",
            "message": f"🌐 {cfg['emoji']} {cfg['name']} login window opened! Log in, then close the window.",
            "platform": platform,
        }

    def _run_login_window(self, platform: str = "threads"):
        """Background thread: opens visible browser, waits for user to log in."""
        cfg = PLATFORMS["threads"]
        profile_dir = str(PROFILES_DIR / "threads")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        except Exception:
            pass

        lock = self._locks.get("threads")
        if lock and not lock.acquire(blocking=True, timeout=10):
            print(f"[BrowserLogin] ⚠️ Could not acquire lock for Threads login window")
            return

        try:
            with sync_playwright() as pw:
                context = pw.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=False,
                    executable_path=_get_browser_args(),
                    slow_mo=80,
                    args=["--no-first-run", "--no-default-browser-check"],
                    viewport={"width": 1280, "height": 800},
                )
                pages = context.pages
                page = pages[0] if pages else context.new_page()
                page.goto(cfg["login_url"], wait_until="domcontentloaded", timeout=30000)

                print(f"[BrowserLogin] 👤 Opened Chrome for {cfg['name']}. Waiting for user login...")

                start_time = time.time()
                while time.time() - start_time < 600:
                    try:
                        active_pages = context.pages
                        if not active_pages:
                            print(f"[BrowserLogin] 🚪 Browser closed by user for {cfg['name']}")
                            break

                        curr_page = active_pages[0]
                        if self._is_logged_in("threads", context, curr_page):
                            print(f"[BrowserLogin] ✅ Threads login detected!")
                            self._update_status("threads", True)
                            _human_delay(2, 3)
                            break
                    except Exception:
                        break

                    time.sleep(1.5)

                try:
                    context.close()
                except Exception:
                    pass

            _human_delay(1, 2)
            final_status = self.check_login_status("threads")
            print(f"[BrowserLogin] 💾 {cfg['name']} session status: {'✅ Logged In' if final_status else '❌ Not Logged In'}")

        except Exception as e:
            print(f"[BrowserLogin] ❌ Login window error for Threads: {e}")
            try:
                self.check_login_status("threads")
            except Exception:
                self._update_status("threads", False)
        finally:
            if lock and lock.locked():
                try:
                    lock.release()
                except RuntimeError:
                    pass

    def check_login_status(self, platform: str = "threads") -> bool:
        """Silently checks if the saved Threads session is valid."""
        if not HAS_PLAYWRIGHT:
            return False

        profile_dir = PROFILES_DIR / "threads"
        if not profile_dir.exists():
            return False

        lock = self._locks.get("threads")
        if lock and not lock.acquire(blocking=False):
            return self._status_cache.get("threads", False)

        cfg = PLATFORMS["threads"]
        try:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            except Exception:
                pass

            _clean_profile_locks(profile_dir)
            with sync_playwright() as pw:
                context = pw.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=True,
                    executable_path=_get_browser_args(),
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                
                if self._is_logged_in("threads", context, None):
                    context.close()
                    self._update_status("threads", True)
                    print(f"[BrowserLogin] {cfg['emoji']} Threads: ✅ Logged In (Cookie Verified)")
                    return True

                page = context.new_page()
                page.goto(cfg["home_url"], wait_until="domcontentloaded", timeout=20000)
                _human_delay(1.5, 3.0)

                logged_in = self._is_logged_in("threads", context, page)
                context.close()
                self._update_status("threads", logged_in)
                return logged_in

        except Exception as e:
            print(f"[BrowserLogin] ⚠️ Status check failed for Threads: {e}")
            return False
        finally:
            if lock and lock.locked():
                try:
                    lock.release()
                except RuntimeError:
                    pass

    def check_all_status(self) -> dict:
        """Check status for Threads."""
        results = {"threads": self.check_login_status("threads")}
        self._save_status()
        return results

    def scrape_leads(self, platform: str = "threads", keyword: str = "convert pdf", limit: int = 5, headless: bool = True) -> list:
        """Scrapes real Threads posts using saved logged-in session."""
        if not HAS_PLAYWRIGHT:
            return []

        profile_dir = PROFILES_DIR / "threads"
        if not profile_dir.exists():
            print(f"[BrowserLogin] ⚠️ No session for Threads. Please log in first.")
            return []

        lock = self._locks.get("threads")
        if lock and not lock.acquire(blocking=True, timeout=10):
            print(f"[BrowserLogin] ⚠️ Could not acquire lock for Threads scrape")
            return []

        cfg = PLATFORMS["threads"]
        search_url = cfg["search_url"].format(keyword=keyword.replace(" ", "+"))
        leads = []

        try:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            except Exception:
                pass

            _clean_profile_locks(profile_dir)
            with sync_playwright() as pw:
                context = pw.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=headless,
                    executable_path=_get_browser_args(),
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                    permissions=["clipboard-read", "clipboard-write"],
                    viewport={"width": 1280, "height": 800},
                )
                page = context.pages[0] if context.pages else context.new_page()

                print(f"[BrowserLogin] 🌐 Navigating to Threads search for '{keyword}'...")
                try:
                    page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
                except Exception as goto_e:
                    print(f"[BrowserLogin] Search navigation notice: {goto_e}")
                _human_delay(3, 5)

                # Search input typing fallback if needed
                search_selectors = ["input[placeholder*='Search']", "input[aria-label*='Search']", "input[type='search']", "input"]
                for sel in search_selectors:
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible() and not page.query_selector("article"):
                            el.click(force=True)
                            _human_delay(0.3, 0.6)
                            page.keyboard.press("Control+A")
                            page.keyboard.press("Backspace")
                            for char in keyword:
                                page.keyboard.type(char)
                                time.sleep(random.uniform(0.04, 0.10))
                            _human_delay(0.5, 1.0)
                            page.keyboard.press("Enter")
                            _human_delay(3, 5)
                            break
                    except Exception:
                        continue

                _human_delay(2, 4)

                # Scroll to discover deep posts
                print(f"[BrowserLogin] 📜 Scrolling Threads for '{keyword}'...")
                for _ in range(random.randint(3, 5)):
                    _random_scroll(page)

                leads = self._extract_threads_posts(page, keyword, limit)
                context.close()

        except Exception as e:
            print(f"[BrowserLogin] ❌ Scrape error for Threads/'{keyword}': {e}")
        finally:
            if lock and lock.locked():
                try:
                    lock.release()
                except RuntimeError:
                    pass

        print(f"[BrowserLogin] 🔍 🧵 Threads — {len(leads)} leads for '{keyword}'")
        return leads

    def _extract_threads_posts(self, page, keyword: str, limit: int) -> list:
        leads = []
        try:
            # DOM evaluator using exact post link anchors (a[href*='/post/'])
            extracted_items = page.evaluate("""() => {
                const results = [];
                const postAnchors = Array.from(document.querySelectorAll("a[href*='/post/']"));
                const seenUrls = new Set();
                for (const anchor of postAnchors) {
                    const href = anchor.getAttribute("href") || "";
                    if (!href) continue;
                    const fullUrl = href.startsWith("http") ? href : "https://www.threads.net" + href;
                    if (seenUrls.has(fullUrl)) continue;
                    seenUrls.add(fullUrl);

                    // Ascend to post card container
                    let parent = anchor.parentElement;
                    for (let i = 0; i < 6 && parent; i++) {
                        if (parent.innerText && parent.innerText.length > 30) {
                            break;
                        }
                        parent = parent.parentElement;
                    }
                    const text = parent ? parent.innerText.trim() : "";
                    if (text && text.length > 15) {
                        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 3 && !['Translate', 'Like', 'Reply', 'Repost', 'Share', 'Copy link'].includes(l));
                        const cleanTitle = lines.length > 1 ? lines.slice(1, 5).join(" ") : (lines[0] || text);
                        results.push({
                            title: cleanTitle.slice(0, 200),
                            url: fullUrl
                        });
                    }
                }
                return results;
            }""")

            for item in extracted_items:
                title = item.get("title", "").strip()
                url = item.get("url", "").strip()
                if not title or not url:
                    continue

                leads.append({
                    "platform": "Threads",
                    "title": title[:180],
                    "url": url,
                    "snippet": title[:300],
                    "keyword": keyword,
                    "reddit_id": None,
                })
                print(f"[Threads UI Extracted] '{title[:50]}...' | Link: {url}")
                if len(leads) >= limit:
                    break

        except Exception as e:
            print(f"[BrowserLogin] Threads extract error: {e}")
        return leads

    def post_reply(self, platform: str = "threads", post_url: str = "", reply_text: str = "", headless: bool = True) -> tuple:
        """Posts a reply/comment on a Threads post using saved session."""
        if not HAS_PLAYWRIGHT:
            return False, "playwright_not_installed"

        profile_dir = PROFILES_DIR / "threads"
        if not profile_dir.exists():
            return False, "no_session_please_login_first"

        lock = self._locks.get("threads")
        if lock and not lock.acquire(blocking=True, timeout=15):
            print(f"[BrowserLogin] ⚠️ Could not acquire lock for Threads reply")
            return False, "lock_acquire_timeout"

        try:
            return self._post_threads_reply(post_url, reply_text, headless=headless)
        except Exception as e:
            return False, f"error_{str(e)[:50]}"
        finally:
            if lock and lock.locked():
                try:
                    lock.release()
                except RuntimeError:
                    pass

    def _post_threads_reply(self, post_url: str, reply_text: str, headless: bool = True) -> tuple:
        """Navigate to Threads post, focus reply box, type comment, submit."""
        profile_dir = str(PROFILES_DIR / "threads")
        _clean_profile_locks(profile_dir)
        try:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            except Exception:
                pass

            with sync_playwright() as pw:
                ctx = pw.chromium.launch_persistent_context(
                    user_data_dir=profile_dir, headless=headless,
                    executable_path=_get_browser_args(),
                    args=["--no-sandbox"],
                    permissions=["clipboard-read", "clipboard-write"],
                )
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                try:
                    page.goto(post_url, wait_until="domcontentloaded", timeout=25000)
                except Exception:
                    pass
                _human_delay(3, 5)

                reply_trigger = page.query_selector("svg[aria-label='Reply'], [aria-label='Reply'], div[role='textbox'], [aria-label='Comment']")
                if reply_trigger:
                    try:
                        reply_trigger.click(force=True)
                    except Exception:
                        page.evaluate("""(el) => {
                            const parent = el.closest('button') || el.closest('div') || el;
                            if (parent && typeof parent.click === 'function') parent.click();
                        }""", reply_trigger)
                    _human_delay(1.5, 2.5)

                reply_input = page.query_selector("div[role='textbox'], div[contenteditable='true']")
                if not reply_input:
                    ctx.close()
                    return False, "threads_reply_input_not_found"

                try:
                    reply_input.click(force=True)
                except Exception:
                    pass
                _human_delay(0.5, 1.0)

                try:
                    page.keyboard.insert_text(reply_text[:300])
                except Exception:
                    for char in reply_text[:300]:
                        page.keyboard.type(char)
                        time.sleep(random.gauss(0.04, 0.01))

                page.evaluate("""() => {
                    const input = document.querySelector("div[role='textbox'], div[contenteditable='true']");
                    if (input) {
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""")

                _human_delay(1.5, 3.0)

                posted_via_js = page.evaluate("""() => {
                    const input = document.querySelector("div[role='textbox'], div[contenteditable='true']");
                    if (input) {
                        let parent = input.parentElement;
                        while (parent && parent.tagName !== 'BODY') {
                            const btns = Array.from(parent.querySelectorAll("div[role='button'], button, span"));
                            const postBtn = btns.find(b => {
                                const txt = b.textContent ? b.textContent.trim() : "";
                                const label = b.getAttribute("aria-label") || "";
                                // Exclude 'Reply' because 'Reply' is the trigger button on the post card!
                                return (txt === "Post" || txt === "Đăng" || txt === "↑" || label === "Post" || label === "Submit") && txt !== "Reply";
                            });
                            if (postBtn) {
                                const target = postBtn.closest("div[role='button']") || postBtn.closest("button") || postBtn;
                                target.click();
                                return true;
                            }
                            parent = parent.parentElement;
                        }
                    }
                    const buttons = Array.from(document.querySelectorAll("div[role='button'], button"));
                    const postBtn = buttons.find(b => {
                        const txt = b.textContent ? b.textContent.trim() : "";
                        const label = b.getAttribute("aria-label") || "";
                        return (txt === "Post" || txt === "Đăng" || txt === "↑" || label === "Post" || label === "Submit") && txt !== "Reply";
                    });
                    if (postBtn) {
                        const target = postBtn.closest("div[role='button']") || postBtn.closest("button") || postBtn;
                        target.click();
                        return true;
                    }
                    return false;
                }""")

                if not posted_via_js:
                    post_btn = page.query_selector("div[role='button']:has-text('Post'), button:has-text('Post'), svg[aria-label='Post']")
                    if post_btn:
                        post_btn.click(force=True)
                        posted_via_js = True

                # Press Control+Enter as guaranteed submit trigger
                try:
                    reply_input.focus()
                    _human_delay(0.3, 0.6)
                    page.keyboard.press("Control+Enter")
                except Exception:
                    pass

                _human_delay(4, 6)

                ctx.close()
                return True, "posted_via_browser"

        except Exception as e:
            return False, f"threads_browser_error_{str(e)[:40]}"

    def import_session_cookies(self, session_id: str, ds_user_id: str = "") -> dict:
        """Inject Threads sessionid and ds_user_id cookies directly into the persistent browser profile."""
        if not HAS_PLAYWRIGHT:
            return {"status": "error", "message": "playwright not installed"}

        session_id = session_id.strip()
        if not session_id:
            return {"status": "error", "message": "sessionid cookie cannot be empty"}

        profile_dir = str(PROFILES_DIR / "threads")
        _clean_profile_locks(profile_dir)

        try:
            with sync_playwright() as pw:
                ctx = pw.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=True,
                    executable_path=_get_browser_args(),
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                cookies_to_set = [
                    {
                        "name": "sessionid",
                        "value": session_id,
                        "domain": ".threads.net",
                        "path": "/",
                        "secure": True,
                        "httpOnly": True,
                        "sameSite": "None",
                    }
                ]
                if ds_user_id.strip():
                    cookies_to_set.append({
                        "name": "ds_user_id",
                        "value": ds_user_id.strip(),
                        "domain": ".threads.net",
                        "path": "/",
                        "secure": True,
                        "httpOnly": False,
                        "sameSite": "None",
                    })
                ctx.add_cookies(cookies_to_set)
                ctx.close()

            self._update_status("threads", True)
            print("[BrowserLogin] ✅ Threads sessionid cookie injected successfully!")
            return {"status": "success", "message": "🧵 Threads Session Cookie saved! Browser authenticated 24/7."}
        except Exception as e:
            return {"status": "error", "message": f"Cookie import failed: {e}"}

    def clear_session(self, platform: str = "threads") -> dict:
        """Delete saved browser profile for Threads."""
        import shutil
        profile_dir = PROFILES_DIR / "threads"
        if profile_dir.exists():
            shutil.rmtree(str(profile_dir))
            self._update_status("threads", False)
            return {"status": "cleared", "message": "🧵 Meta Threads session cleared — login again to reconnect."}
        return {"status": "ok", "message": "No session found for Threads"}

    def get_all_status(self) -> dict:
        """Return cached login status for Threads."""
        cfg = PLATFORMS["threads"]
        profile_exists = (PROFILES_DIR / "threads").exists()
        return {
            "threads": {
                "name":           cfg["name"],
                "emoji":          cfg["emoji"],
                "logged_in":      self._status_cache.get("threads", False),
                "profile_exists": profile_exists,
                "login_url":      cfg["login_url"],
            }
        }

    def _update_status(self, platform: str, logged_in: bool):
        self._status_cache["threads"] = logged_in
        self._save_status()

    def _save_status(self):
        try:
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._status_cache, f, indent=2)
        except Exception:
            pass

    def _load_status(self):
        try:
            if STATUS_FILE.exists():
                with open(STATUS_FILE, "r", encoding="utf-8") as f:
                    self._status_cache = json.load(f)
        except Exception:
            self._status_cache = {}

    def run_full_dynamic_workflow(self, platform: str = "threads", keyword: str = "convert pdf", limit: int = 3, headless: bool = True) -> dict:
        """Executes complete dynamic workflow exclusively on Meta Threads in a single browser session."""
        from modules.ai_engine import AIEngine
        from modules.platform_posters import load_history, save_history
        from modules.telegram_notifier import send_telegram_alert, send_simple_message
        from modules.human_behavior import human

        profile_dir = str(PROFILES_DIR / "threads")
        if not (PROFILES_DIR / "threads").exists():
            return {"status": "error", "message": "No Threads session found. Log in first."}

        lock = self._locks.get("threads")
        if lock and not lock.acquire(blocking=True, timeout=15):
            return {"status": "error", "message": "Could not acquire browser lock."}

        print(f"\n🚀 [Dynamic Threads Workflow] Starting single-session scan for '{keyword}'...")
        send_simple_message(f"🚀 <b>SEO Bot Threads Scan:</b> Starting Threads browser session...\nSearching for keyword: <b>'{keyword}'</b>")

        processed_leads = []
        ai = AIEngine()
        history = load_history()
        existing_urls = {h.get("url") for h in history}

        try:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            except Exception:
                pass

            _clean_profile_locks(profile_dir)
            with sync_playwright() as pw:
                ctx = pw.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=headless,
                    executable_path=_get_browser_args(),
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                    permissions=["clipboard-read", "clipboard-write"],
                    viewport={"width": 1280, "height": 850},
                )
                page = ctx.pages[0] if ctx.pages else ctx.new_page()

                # Step 1: Search Threads
                search_url = PLATFORMS["threads"]["search_url"].format(keyword=keyword.replace(" ", "+"))
                print(f"[BrowserLogin] 🌐 Navigating to Threads search for '{keyword}'...")
                try:
                    page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
                except Exception as goto_e:
                    print(f"[BrowserLogin] Search navigation notice: {goto_e}")
                _human_delay(3, 5)

                for _ in range(random.randint(2, 4)):
                    _random_scroll(page)

                raw_leads = self._extract_threads_posts(page, keyword, limit=limit * 2)
                print(f"[BrowserLogin] 🔍 Found {len(raw_leads)} potential Threads posts.")

                # Step 2: Auto-reply on each new lead in SAME session
                for post in raw_leads:
                    url = post.get("url", "")
                    title = post.get("title", "")
                    if not url or url in existing_urls:
                        continue
                    existing_urls.add(url)

                    post_text = f"{title}\n{post.get('snippet', '')}"
                    ai_res = ai.analyze_and_draft_reply(post_text, platform="Threads")

                    if ai_res and not ai_res.get("error"):
                        reply_text = ai_res.get("reply_text")
                        intent = ai_res.get("intent_summary")
                        matched_url = ai_res.get("matched_url", "https://mr-converter.com")
                    else:
                        reply_text = f"You can convert and edit your files online for free at https://mr-converter.com"
                        intent = f"Needs {keyword} tool"
                        matched_url = "https://mr-converter.com"

                    reply_text = human.humanize_reply(reply_text, platform="Threads")
                    lead_id = f"threads_{abs(hash(url)) % 1000000000}"

                    print(f"\n💬 [Replying on Lead] {url}...")
                    posted_status = "lead_captured_ready_to_reply"

                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=25000)
                        _human_delay(3, 4)

                        reply_trigger = page.query_selector("svg[aria-label='Reply'], [aria-label='Reply'], div[role='textbox'], [aria-label='Comment']")
                        if reply_trigger:
                            try:
                                reply_trigger.click(force=True)
                            except Exception:
                                pass
                            _human_delay(1.5, 2.5)

                        reply_input = page.query_selector("div[role='textbox'], div[contenteditable='true']")
                        if reply_input:
                            reply_input.click(force=True)
                            _human_delay(0.5, 1.0)
                            try:
                                page.keyboard.insert_text(reply_text[:300])
                            except Exception:
                                page.keyboard.type(reply_text[:300])

                            page.evaluate("""() => {
                                const input = document.querySelector("div[role='textbox'], div[contenteditable='true']");
                                if (input) {
                                    input.dispatchEvent(new Event('input', { bubbles: true }));
                                    input.dispatchEvent(new Event('change', { bubbles: true }));
                                }
                            }""")

                            _human_delay(1.5, 2.5)

                            posted_via_js = page.evaluate("""() => {
                                const input = document.querySelector("div[role='textbox'], div[contenteditable='true']");
                                if (input) {
                                    let parent = input.parentElement;
                                    while (parent && parent.tagName !== 'BODY') {
                                        const btns = Array.from(parent.querySelectorAll("div[role='button'], button, span"));
                                        const postBtn = btns.find(b => {
                                            const txt = b.textContent ? b.textContent.trim() : "";
                                            const label = b.getAttribute("aria-label") || "";
                                            return (txt === "Post" || txt === "Đăng" || txt === "↑" || label === "Post" || label === "Submit") && txt !== "Reply";
                                        });
                                        if (postBtn) {
                                            const target = postBtn.closest("div[role='button']") || postBtn.closest("button") || postBtn;
                                            target.click();
                                            return true;
                                        }
                                        parent = parent.parentElement;
                                    }
                                }
                                const buttons = Array.from(document.querySelectorAll("div[role='button'], button"));
                                const postBtn = buttons.find(b => {
                                    const txt = b.textContent ? b.textContent.trim() : "";
                                    const label = b.getAttribute("aria-label") || "";
                                    return (txt === "Post" || txt === "Đăng" || txt === "↑" || label === "Post" || label === "Submit") && txt !== "Reply";
                                });
                                if (postBtn) {
                                    const target = postBtn.closest("div[role='button']") || postBtn.closest("button") || postBtn;
                                    target.click();
                                    return true;
                                }
                                return false;
                            }""")

                            if not posted_via_js:
                                post_btn = page.query_selector("div[role='button']:has-text('Post'), button:has-text('Post'), svg[aria-label='Post']")
                                if post_btn:
                                    post_btn.click(force=True)

                            try:
                                reply_input.focus()
                                page.keyboard.press("Control+Enter")
                            except Exception:
                                pass

                            _human_delay(4, 6)
                            posted_status = "posted_automatically"
                    except Exception as post_e:
                        print(f"   Posting notice: {post_e}")

                    record = {
                        "id": lead_id,
                        "platform": "Threads",
                        "title": title,
                        "url": url,
                        "intent": intent,
                        "matched_url": matched_url,
                        "reply_text": reply_text,
                        "status": posted_status,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }

                    save_history(record)
                    send_telegram_alert(record)
                    processed_leads.append(record)

                    if len(processed_leads) >= limit:
                        break

                ctx.close()

        except Exception as e:
            print(f"[BrowserLogin] Workflow error: {e}")
        finally:
            if lock and lock.locked():
                try:
                    lock.release()
                except RuntimeError:
                    pass

        send_simple_message(
            f"🎉 <b>Threads Scan Complete!</b>\n"
            f"Processed <b>{len(processed_leads)} NEW real Threads posts</b> for keyword <b>'{keyword}'</b> using Gemini AI.\n"
            f"Cards delivered to your Telegram app!"
        )

        return {
            "status": "success",
            "platform": "Threads",
            "keyword": keyword,
            "leads_found": len(processed_leads),
            "leads": processed_leads
        }


browser_mgr = BrowserSessionManager()
