"""
HumanBehaviorEngine — Perfect Human-like Behavior Simulation
=============================================================
সোশ্যাল মিডিয়া বট ডিটেকশন থেকে সম্পূর্ণ বাঁচার জন্য তৈরি।

৭টি Subsystem:
  A. Gaussian Random Delays        — robotic fixed-sleep এর বদলে প্রকৃত human timing
  B. Daily Activity Window         — রাত ১২–৭টা ঘুম, রাতে কোনো action নেই
  C. Daily Action Budget           — প্রতিটি প্ল্যাটফর্মের দৈনিক সীমা
  D. Typo & Self-Correction        — টাইপের সময় মাঝে মাঝে ভুল → ঠিক করা
  E. Reply Text Variation          — opener rotation + emoji variation
  F. Session Fatigue Modeling      — বেশি কাজে ক্লান্তি → automatic slow-down + break
  G. API Call Jitter               — HTTP request এর আগে micro random pause
"""

import sys
import time
import random
import math
import json
import datetime
from pathlib import Path

# Ensure UTF-8 output so emoji log lines don't crash on Windows cp1252 terminals
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ─────────────────────────────────────────────────────────────
# Constants & Config
# ─────────────────────────────────────────────────────────────

# Daily budget per platform (min, max) — random কারণে রোজ সামান্য ভিন্ন হবে
DAILY_BUDGETS = {
    "reddit":        (8,  13),
    "twitter":       (10, 18),
    "threads":       (12, 20),
    "stackoverflow": (5,  10),
    "facebook":      (6,  10),
    "default":       (8,  15),
}

# Active hour window: start_hour (inclusive) to end_hour (exclusive)
# রাত ১২টা–সকাল ৭টা ঘুমাবে, বাকি সময় কাজ করবে
ACTIVE_HOUR_START = 7    # 7 AM
ACTIVE_HOUR_END   = 23   # 11 PM

# Reply opener rotation — ৬ ভ্যারিয়েন্ট, monotone স্প্যাম ভাব দূর করে
REPLY_OPENERS = [
    "",                              # (no prefix — direct, natural)
    "Hey, just saw this — ",
    "Not sure if this helps, but ",
    "I actually ran into the same thing — ",
    "Quick note: ",
    "This might be what you're looking for — ",
    "Stumbled across this and thought it might help: ",
    "In case it's useful — ",
]

# Single emoji variants (used sparingly — 40% chance, max 1 per reply)
REPLY_EMOJIS = ["👍", "🙌", "✅", "🔗", "💡", "📄", "🗂️"]

# Fatigue threshold: after this many actions per session, slow down kicks in
FATIGUE_THRESHOLD = 3
# After FATIGUE_HARD_STOP actions per session, mandatory long break
FATIGUE_HARD_STOP = 6

# Budget state file path (persisted across restarts)
_BUDGET_FILE = Path(__file__).resolve().parent.parent / "data" / "daily_budget.json"


# ─────────────────────────────────────────────────────────────
# Gaussian helper
# ─────────────────────────────────────────────────────────────

def _gauss_clamp(mean: float, sigma: float, min_val: float, max_val: float) -> float:
    """Gaussian random float, clamped to [min_val, max_val]."""
    val = random.gauss(mean, sigma)
    return max(min_val, min(max_val, val))


# ─────────────────────────────────────────────────────────────
# Main Engine
# ─────────────────────────────────────────────────────────────

class HumanBehaviorEngine:
    """
    Drop-in replacement for all time.sleep() calls across the SEO-bot.
    Use a single shared instance (imported from this module as `human`).
    """

    def __init__(self):
        self._session_action_count = 0   # Actions taken in the current run session
        self._daily_budget = {}          # {platform: {"used": int, "limit": int, "date": str}}
        self._load_budget()
        print("[HumanEngine] ✅ Human Behavior Engine initialized — stealth mode ON")

    # ──────────────────────────────────────────────────────────
    # A. Gaussian Random Delays
    # ──────────────────────────────────────────────────────────

    def jitter_delay(self, label: str = ""):
        """
        Micro jitter before any HTTP/API call (0.3 – 1.8 sec).
        ব্যবহার: প্রতিটি HTTP request পাঠানোর আগে।
        """
        delay = _gauss_clamp(mean=0.9, sigma=0.4, min_val=0.3, max_val=1.8)
        self._sleep(delay, f"jitter{' [' + label + ']' if label else ''}")

    def short_pause(self, label: str = ""):
        """
        Short pause between minor actions (0.8 – 4.5 sec).
        ব্যবহার: keyword loop এর ভেতরে, ছোট ছোট অ্যাকশনের মাঝে।
        """
        delay = _gauss_clamp(mean=2.0, sigma=0.9, min_val=0.8, max_val=4.5)
        self._sleep(delay, f"short_pause{' [' + label + ']' if label else ''}")

    def read_pause(self, label: str = ""):
        """
        Pause simulating reading a post (3 – 13 sec).
        ব্যবহার: পোস্ট পড়া, reply লেখা, AI call এর পরে।
        """
        delay = _gauss_clamp(mean=6.5, sigma=2.5, min_val=3.0, max_val=13.0)
        self._sleep(delay, f"read_pause{' [' + label + ']' if label else ''}")

    def after_post_pause(self, label: str = ""):
        """
        Pause after posting a comment/reply (5 – 22 sec).
        ব্যবহার: সফলভাবে reply/comment পোস্ট করার পরে।
        মানুষ পোস্ট করে একটু দেখে তারপর পরের কাজে যায়।
        """
        delay = _gauss_clamp(mean=11.0, sigma=4.0, min_val=5.0, max_val=22.0)
        self._sleep(delay, f"after_post{' [' + label + ']' if label else ''}")

    def long_break(self, label: str = ""):
        """
        Mid-session break (2 – 9 minutes).
        ব্যবহার: অনেকক্ষণ কাজ করার পরে নিজেই ডাকা হবে।
        """
        delay = _gauss_clamp(mean=300.0, sigma=90.0, min_val=120.0, max_val=540.0)
        mins = delay / 60
        print(f"[HumanEngine] ☕ Taking a long break ({mins:.1f} min)…")
        self._sleep(delay, f"long_break{' [' + label + ']' if label else ''}")

    def typing_delay_for(self, text: str) -> float:
        """
        Return total typing time (seconds) for a given text.
        Characters per minute range: 180 – 280 (real human typing).
        Does NOT sleep — caller decides when to apply it.
        """
        cpm = _gauss_clamp(mean=230, sigma=30, min_val=180, max_val=280)
        cps = cpm / 60.0
        base = len(text) / cps
        # Add micro-variance: ±20%
        variance = random.uniform(0.8, 1.2)
        return round(base * variance, 2)

    def simulate_typing(self, text: str, label: str = ""):
        """
        Sleep for realistic typing duration for the given text.
        ব্যবহার: comment/reply submit করার আগে।
        """
        delay = self.typing_delay_for(text)
        self._sleep(delay, f"typing{' [' + label + ']' if label else ''}")

    # ──────────────────────────────────────────────────────────
    # B. Daily Activity Window — রাতে ঘুম
    # ──────────────────────────────────────────────────────────

    def is_active_hour(self) -> bool:
        """
        Returns True only during human working hours.
        রাত 12 – সকাল 7 = False (ঘুমের সময়, কোনো action নেই)।
        সকাল 7 – রাত 11 = True (কাজের সময়)।
        """
        now = datetime.datetime.now()
        hour = now.hour
        return ACTIVE_HOUR_START <= hour < ACTIVE_HOUR_END

    def wait_for_active_hour(self):
        """
        If called outside active hours, sleep until the start of the next
        active window (7 AM).  Used by the scheduler loop.
        """
        if self.is_active_hour():
            return

        now = datetime.datetime.now()
        # Compute next 7 AM
        next_active = now.replace(hour=ACTIVE_HOUR_START, minute=0, second=0, microsecond=0)
        if now.hour >= ACTIVE_HOUR_END:
            next_active += datetime.timedelta(days=1)

        wait_seconds = (next_active - now).total_seconds()
        # Add small random offset so we don't always wake at exactly 7:00:00
        wait_seconds += random.uniform(0, 900)  # 0–15 min random start variation

        hours_left = wait_seconds / 3600
        print(f"[HumanEngine] 🌙 Outside active hours ({now.strftime('%H:%M')}). "
              f"Sleeping until ~{next_active.strftime('%H:%M')} ({hours_left:.1f}h)…")
        time.sleep(wait_seconds)

    # ──────────────────────────────────────────────────────────
    # C. Daily Action Budget
    # ──────────────────────────────────────────────────────────

    def can_act(self, platform: str) -> bool:
        """
        Check if we're within today's action budget for a platform.
        Returns True = OK to proceed, False = daily limit reached.
        """
        self._refresh_budget_if_new_day()
        platform = platform.lower()
        entry = self._daily_budget.get(platform)
        if not entry:
            # Initialize budget for this platform
            lo, hi = DAILY_BUDGETS.get(platform, DAILY_BUDGETS["default"])
            limit = random.randint(lo, hi)
            entry = {"used": 0, "limit": limit, "date": self._today()}
            self._daily_budget[platform] = entry
            self._save_budget()

        if entry["used"] >= entry["limit"]:
            print(f"[HumanEngine] 🛑 Daily budget exhausted for [{platform}] "
                  f"({entry['used']}/{entry['limit']} actions used today)")
            return False
        return True

    def record_action(self, platform: str):
        """Call this after every successful action (post/comment/reply)."""
        self._refresh_budget_if_new_day()
        platform = platform.lower()
        if platform not in self._daily_budget:
            self.can_act(platform)  # Initialize if missing
        self._daily_budget[platform]["used"] += 1
        self._save_budget()
        self._session_action_count += 1

        used  = self._daily_budget[platform]["used"]
        limit = self._daily_budget[platform]["limit"]
        print(f"[HumanEngine] 📊 [{platform}] Action recorded — {used}/{limit} today "
              f"| Session: {self._session_action_count}")

    def budget_status(self) -> dict:
        """Return current daily budget status for all platforms (for dashboard)."""
        self._refresh_budget_if_new_day()
        return {
            platform: {
                "used":      data["used"],
                "limit":     data["limit"],
                "remaining": max(0, data["limit"] - data["used"]),
                "date":      data["date"],
            }
            for platform, data in self._daily_budget.items()
        }

    # ──────────────────────────────────────────────────────────
    # D. Typo & Self-Correction Simulation
    # ──────────────────────────────────────────────────────────

    def add_human_typo_feel(self, text: str, typo_probability: float = 0.15) -> str:
        """
        Simulate human typing imperfection.

        With `typo_probability` chance, randomly doubles one interior character
        (keyboard slip) then removes it — net result: text unchanged, but we
        *simulate* the pause (an extra short_pause is added internally).

        Returns the corrected text (same as input) after simulating the typo/fix.
        The caller should use the returned text for posting — it is always correct.
        """
        if random.random() > typo_probability or len(text) < 6:
            return text

        # Pick a random interior character position to "slip"
        slip_pos = random.randint(2, len(text) - 3)
        slipped_char = text[slip_pos]

        # Simulate: type up to slip, accidentally double the character, pause, backspace
        print(f"[HumanEngine] ⌨️  Simulating typo at pos {slip_pos} ('{slipped_char}') — correcting…")
        time.sleep(random.uniform(0.4, 1.1))  # Typing up to typo point
        time.sleep(random.uniform(0.3, 0.8))  # Noticing the mistake
        time.sleep(random.uniform(0.2, 0.5))  # Backspace correction

        # Return original (correct) text — the typo was in the simulation only
        return text

    # ──────────────────────────────────────────────────────────
    # E. Reply Text Variation
    # ──────────────────────────────────────────────────────────

    def vary_reply_opener(self, reply_text: str) -> str:
        """
        Rotate reply openers and optionally append a single emoji.
        Prevents identical replies from triggering spam filters.

        Rules:
        - 60% chance: prepend a varied opener
        - 40% chance: append a single relevant emoji
        - Never adds more than 1 emoji
        - Never changes the core helpful content
        """
        result = reply_text.strip()

        # Opener rotation (60% chance)
        if random.random() < 0.60:
            opener = random.choice(REPLY_OPENERS)
            if opener:
                # Lowercase the first letter of original text if opener ends with space
                if opener.endswith((" ", "— ", ": ")):
                    result = opener + result[0].lower() + result[1:]
                else:
                    result = opener + result

        # Single emoji (40% chance, appended at end)
        if random.random() < 0.40:
            emoji = random.choice(REPLY_EMOJIS)
            # Only add if text doesn't already end with an emoji-like character
            if not result.endswith(("!", ".", "?", "😊", "👍", "✅", "💡", "🔗")):
                result = result + " " + emoji

        return result

    def vary_reply_length(self, reply_text: str) -> str:
        """
        Occasionally shorten or expand reply for natural variation.
        - 20% chance: strip last sentence (shorter, casual feel)
        - 10% chance: add a warm closing line
        Returns modified reply text.
        """
        sentences = [s.strip() for s in reply_text.replace("!", ".").split(".") if s.strip()]

        roll = random.random()
        if roll < 0.20 and len(sentences) > 2:
            # Drop last sentence — feel more casual
            shorter = ". ".join(sentences[:-1]) + "."
            return shorter
        elif roll < 0.30:
            # Add a warm closing
            closings = [
                " Hope this helps!",
                " Let me know if you need anything else.",
                " Good luck!",
            ]
            return reply_text.rstrip(".!") + random.choice(closings)

        return reply_text

    def humanize_reply(self, reply_text: str, platform: str = "") -> str:
        """
        Full pipeline: vary opener + length + typo simulation.
        Call this ONCE on every reply_text before posting.
        """
        result = self.vary_reply_opener(reply_text)
        result = self.vary_reply_length(result)
        result = self.add_human_typo_feel(result)
        return result

    # ──────────────────────────────────────────────────────────
    # F. Session Fatigue Modeling
    # ──────────────────────────────────────────────────────────

    def session_fatigue_check(self, platform: str = ""):
        """
        Called after each action. Applies fatigue-based slowdown:
        - Actions 1–3:  normal speed (no extra delay)
        - Actions 4–6:  1.5× read_pause (getting tired)
        - Actions 7+:   mandatory long break (5–15 min)
        """
        n = self._session_action_count

        if n < FATIGUE_THRESHOLD:
            return  # Fresh — proceed at full speed

        if FATIGUE_THRESHOLD <= n < FATIGUE_HARD_STOP:
            # Getting tired — slow down
            fatigue_delay = _gauss_clamp(mean=9.0, sigma=3.0, min_val=5.0, max_val=18.0)
            print(f"[HumanEngine] 😴 Fatigue level {n - FATIGUE_THRESHOLD + 1} — "
                  f"slowing down ({fatigue_delay:.1f}s pause)…")
            time.sleep(fatigue_delay)
            return

        # Hard stop — mandatory break
        break_seconds = _gauss_clamp(mean=480, sigma=120, min_val=300, max_val=900)
        mins = break_seconds / 60
        print(f"[HumanEngine] 🛑 Session hard-stop after {n} actions. "
              f"Mandatory break: {mins:.1f} min…")
        time.sleep(break_seconds)
        # Reset session counter after break
        self._session_action_count = 0
        print(f"[HumanEngine] ✅ Break over — session counter reset. Resuming…")

    def reset_session(self):
        """Manually reset the session action counter (e.g., on new scheduler cycle)."""
        self._session_action_count = 0

    # ──────────────────────────────────────────────────────────
    # G. API Call Jitter (helper for all HTTP requests)
    # ──────────────────────────────────────────────────────────

    def before_request(self, platform: str = "", action: str = ""):
        """
        Call this immediately before any HTTP/API request.
        Adds a realistic micro-pause so requests are never fired instantly.
        """
        # Base jitter
        jitter = _gauss_clamp(mean=0.7, sigma=0.3, min_val=0.2, max_val=1.6)
        label = f"{platform} {action}".strip()
        if label:
            print(f"[HumanEngine] ⏱  Pre-request jitter ({jitter:.2f}s) [{label}]")
        time.sleep(jitter)

    # ──────────────────────────────────────────────────────────
    # Session Gap (for scheduler between full scan cycles)
    # ──────────────────────────────────────────────────────────

    def session_gap(self, configured_minutes: int = 15) -> float:
        """
        Return a human-like interval (seconds) between two full scan cycles.
        Adds ±20% Gaussian variance around the configured interval.
        """
        base = configured_minutes * 60
        variance_factor = _gauss_clamp(mean=1.0, sigma=0.12, min_val=0.75, max_val=1.30)
        actual = base * variance_factor
        actual_min = actual / 60
        print(f"[HumanEngine] ⏰ Next scan in {actual_min:.1f} min "
              f"(configured: {configured_minutes} min, variance applied)")
        return actual

    # ──────────────────────────────────────────────────────────
    # Demo / Debug
    # ──────────────────────────────────────────────────────────

    def demo_all_delays(self):
        """Quick smoke-test: print delay values for all pause types without sleeping."""
        print("\n=== HumanBehaviorEngine — Delay Demo (no actual sleep) ===")
        samples = {
            "jitter_delay":      [_gauss_clamp(0.9, 0.4, 0.3, 1.8) for _ in range(5)],
            "short_pause":       [_gauss_clamp(2.0, 0.9, 0.8, 4.5) for _ in range(5)],
            "read_pause":        [_gauss_clamp(6.5, 2.5, 3.0, 13.0) for _ in range(5)],
            "after_post_pause":  [_gauss_clamp(11.0, 4.0, 5.0, 22.0) for _ in range(5)],
            "long_break (min)":  [_gauss_clamp(300, 90, 120, 540) / 60 for _ in range(3)],
        }
        for name, vals in samples.items():
            formatted = [f"{v:.2f}" for v in vals]
            print(f"  {name:22s}: {formatted}")
        print()

        print("  Reply openers (5 samples):")
        sample_reply = "You can use this free converter at https://mr-converter.com"
        for _ in range(5):
            print(f"    → {self.vary_reply_opener(sample_reply)}")
        print()

        print("  Activity window right now:", "✅ ACTIVE" if self.is_active_hour() else "🌙 SLEEPING")
        print("  Daily budgets:", self.budget_status())
        print("=== Demo complete ===\n")

    # ──────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────

    def _sleep(self, seconds: float, label: str = ""):
        """Internal sleep with consistent logging."""
        if label:
            print(f"[HumanEngine] ⏳ {label}: {seconds:.2f}s")
        time.sleep(seconds)

    def _today(self) -> str:
        return datetime.date.today().isoformat()

    def _refresh_budget_if_new_day(self):
        """Reset all platform budgets at the start of a new calendar day."""
        today = self._today()
        needs_reset = any(
            entry.get("date") != today
            for entry in self._daily_budget.values()
        )
        if needs_reset:
            print(f"[HumanEngine] 📅 New day ({today}) — resetting all daily budgets")
            for platform in list(self._daily_budget.keys()):
                lo, hi = DAILY_BUDGETS.get(platform, DAILY_BUDGETS["default"])
                self._daily_budget[platform] = {
                    "used":  0,
                    "limit": random.randint(lo, hi),  # slightly different each day
                    "date":  today,
                }
            self._save_budget()

    def _load_budget(self):
        """Load persisted daily budget from disk."""
        try:
            if _BUDGET_FILE.exists():
                with open(_BUDGET_FILE, "r", encoding="utf-8") as f:
                    self._daily_budget = json.load(f)
                self._refresh_budget_if_new_day()
                print(f"[HumanEngine] 📂 Budget loaded: {self.budget_status()}")
            else:
                self._daily_budget = {}
        except Exception as e:
            print(f"[HumanEngine] ⚠️  Could not load budget: {e} — starting fresh")
            self._daily_budget = {}

    def _save_budget(self):
        """Persist daily budget to disk so it survives restarts."""
        try:
            _BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(_BUDGET_FILE, "w", encoding="utf-8") as f:
                json.dump(self._daily_budget, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[HumanEngine] ⚠️  Could not save budget: {e}")


# ─────────────────────────────────────────────────────────────
# Global shared instance — import this everywhere
# ─────────────────────────────────────────────────────────────
human = HumanBehaviorEngine()
