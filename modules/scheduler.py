import time
import threading
from config import load_config
from modules.real_scraper import RealLeadFetcher
from modules.threads_listener import ThreadsListener
from modules.human_behavior import human


class BackgroundScheduler:
    def __init__(self):
        self._running = False
        self._thread = None

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            print("Background 24/7 Threads Scheduler Started!")

    def stop(self):
        self._running = False
        print("Background Threads Scheduler Stopped.")

    def _loop(self):
        while self._running:
            config = load_config()
            if config.get("automation_active", False):

                # ── Night-time guard ──────────────────────────────────────────
                if not human.is_active_hour():
                    human.wait_for_active_hour()
                    continue

                ts = time.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{ts}] ===== Running Meta Threads automated scan cycle =====")

                human.reset_session()

                # 1. Threads Official API Auto-Reply
                try:
                    threads = ThreadsListener(config)
                    t_res = threads.run_scan()
                    if t_res.get("status") != "skipped":
                        print(f"[Threads API] {t_res.get('leads_found',0)} leads | Auto-replied: {t_res.get('auto_replied',0)}")
                except Exception as e:
                    print(f"[Threads API] Error: {e}")

                # 2. Threads Browser Real Scraper
                try:
                    fetcher = RealLeadFetcher(config)
                    result = fetcher.fetch_all(max_per_keyword=3)
                    commented = result.get("threads_auto_commented", 0)
                    print(f"[Threads Browser Scraper] {result['count']} new leads | Browser auto-commented: {commented}")
                except Exception as e:
                    print(f"[Threads Browser Scraper] Error: {e}")

                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ===== Meta Threads scan cycle complete =====")

            configured_minutes = config.get("scan_interval_minutes", 15)
            actual_interval = human.session_gap(configured_minutes)
            for _ in range(int(actual_interval / 10)):
                if not self._running:
                    break
                time.sleep(10)


global_scheduler = BackgroundScheduler()
