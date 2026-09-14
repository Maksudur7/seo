import sys, os
if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from contextlib import asynccontextmanager

import time
from config import load_config, save_config
from modules.site_crawler import SiteCrawler, load_site_index
from modules.platform_posters import load_history, save_history
from modules.threads_listener import ThreadsListener
from modules.ai_engine import AIEngine
from modules.telegram_notifier import send_telegram_alert
from modules.scheduler import global_scheduler
from modules.real_scraper import RealLeadFetcher
from modules.telegram_callback import telegram_callback_handler
from modules.browser_login import browser_mgr

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Meta Threads SEO Bot Server...")
    config = load_config()
    telegram_callback_handler.start()
    if config.get("automation_active", False):
        global_scheduler.start()
    yield
    global_scheduler.stop()
    telegram_callback_handler.stop()

app = FastAPI(title="Meta Threads Social Marketing Automation Hub", lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/config")
async def get_configuration():
    return JSONResponse(content=load_config())

@app.post("/api/config")
async def update_configuration(request: Request):
    data = await request.json()
    save_config(data)
    
    current_cfg = load_config()
    if current_cfg.get("automation_active", False):
        global_scheduler.start()
    else:
        global_scheduler.stop()

    return JSONResponse(content={"status": "success", "config": current_cfg})

@app.post("/api/crawl")
async def trigger_crawl():
    config = load_config()
    target_url = config.get("target_website_url", "")
    if not target_url:
        return JSONResponse(content={"status": "error", "message": "Target website URL is missing!"}, status_code=400)

    crawler = SiteCrawler(target_url)
    res = crawler.crawl(max_pages=30)
    return JSONResponse(content=res)

@app.get("/api/site-index")
async def get_site_index():
    return JSONResponse(content=load_site_index())

@app.post("/api/scan")
async def trigger_scan():
    config = load_config()
    threads_listener = ThreadsListener(config)
    t_res = threads_listener.run_scan()

    return JSONResponse(content={
        "status": "success",
        "threads": t_res,
        "history": load_history()
    })

@app.post("/api/test-lead")
async def trigger_test_lead():
    config = load_config()
    api_key = config.get("gemini_api_key", "").strip()
    target_url = config.get("target_website_url", "").strip() or "https://mr-converter.com"
    
    reply_text = ""
    intent = "Needs PDF converter tool"
    matched_url = f"{target_url.rstrip('/')}/tools/pdf-merge"
    sample_post = "Does anyone know a good free tool to convert PDF files to Word documents on Threads?"

    if api_key and api_key.startswith("AIzaSy"):
        try:
            ai = AIEngine(api_key)
            ai_res = ai.analyze_and_draft_reply(sample_post, platform="Threads")
            if ai_res and not ai_res.get("error"):
                reply_text = ai_res.get("reply_text")
                intent = ai_res.get("intent_summary", intent)
                matched_url = ai_res.get("matched_url", matched_url)
        except Exception as e:
            print(f"Test lead AI fallback: {e}")

    if not reply_text:
        reply_text = f"You can convert and merge your PDF files online for free here: {matched_url}"

    record = {
        "id": f"threads_test_{int(time.time())}",
        "platform": "Threads",
        "title": sample_post,
        "url": "https://www.threads.net/@demo_user/post/test123456",
        "intent": intent,
        "matched_url": matched_url,
        "reply_text": reply_text,
        "status": "tested_successfully",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    save_history(record)
    telegram_sent = send_telegram_alert(record)
    
    return JSONResponse(content={
        "status": "success",
        "record": record,
        "telegram_sent": telegram_sent,
        "message": "🎉 Test Threads Lead Generated Successfully! Check your Telegram App and Live Feed below."
    })

@app.post("/api/fetch-live-leads")
async def trigger_fetch_live_leads():
    """Fetches REAL live Meta Threads posts using logged-in browser session & API."""
    config = load_config()

    fetcher = RealLeadFetcher(config)
    result = fetcher.fetch_all(max_per_keyword=3)

    if result["count"] == 0:
        result["message"] = (
            f"✅ Scanned Threads posts, but no NEW leads found yet. "
            "All matching posts may already be in your history. Try adding more keywords or wait for new posts."
        )
    else:
        result["message"] = (
            f"🎉 Successfully fetched {result['count']} REAL live Meta Threads leads! Check your Telegram App."
        )

    return JSONResponse(content=result)

@app.get("/api/history")
async def get_history_records():
    return JSONResponse(content=load_history())

@app.post("/api/generate-reply")
async def generate_custom_reply(request: Request):
    data = await request.json()
    post_text = data.get("post_text", "").strip()
    platform = data.get("platform", "Threads")
    if not post_text:
        return JSONResponse(content={"status": "error", "message": "Post text missing!"}, status_code=400)
    
    config = load_config()
    api_key = config.get("gemini_api_key", "").strip()
    ai = AIEngine(api_key)
    res = ai.analyze_and_draft_reply(post_text, platform=platform)
    if "error" in res:
        return JSONResponse(content={"status": "error", "message": res["error"]}, status_code=400)
    
    return JSONResponse(content={"status": "success", "result": res})

# ─────────────────────────────────────────────────────────────
# Browser Login Manager Endpoints (Threads Exclusive)
# ─────────────────────────────────────────────────────────────

@app.get("/api/browser-status")
async def get_browser_status():
    status = browser_mgr.get_all_status()
    return JSONResponse(content={"status": "success", "platforms": status})

@app.post("/api/browser-login/{platform}")
async def open_browser_login(platform: str):
    import asyncio
    result = await asyncio.to_thread(browser_mgr.open_login_window, "threads")
    return JSONResponse(content=result)

@app.post("/api/browser-check/{platform}")
async def check_browser_session(platform: str):
    import asyncio
    logged_in = await asyncio.to_thread(browser_mgr.check_login_status, "threads")
    return JSONResponse(content={"platform": "threads", "logged_in": logged_in})

@app.post("/api/browser-cookie/{platform}")
async def import_browser_cookie(platform: str, request: Request):
    import asyncio
    data = await request.json()
    session_id = data.get("session_id", "").strip()
    ds_user_id = data.get("ds_user_id", "").strip()
    result = await asyncio.to_thread(browser_mgr.import_session_cookies, session_id, ds_user_id)
    return JSONResponse(content=result)

@app.delete("/api/browser-session/{platform}")
async def clear_browser_session(platform: str):
    import asyncio
    result = await asyncio.to_thread(browser_mgr.clear_session, "threads")
    return JSONResponse(content=result)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
