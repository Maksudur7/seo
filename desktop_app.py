import sys
import os
import time
import threading
import webbrowser
import requests
from pathlib import Path
from PIL import Image, ImageDraw

# Ensure stdout and stderr exist in PyInstaller windowed mode
class NullWriter:
    def write(self, text): pass
    def flush(self): pass
    def reconfigure(self, **kwargs): pass

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()

# Ensure PyInstaller executable root folder is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Import FastAPI app from app.py
from app import app
import uvicorn

SERVER_PORT = 8000
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"

def create_tray_icon_image():
    """Generates a sleek, modern Threads purple/pink gradient icon for System Tray."""
    width = 64
    height = 64
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    
    # Outer rounded circle
    dc.ellipse([2, 2, 62, 62], fill=(16, 185, 129, 255), outline=(255, 255, 255, 220), width=3)
    
    # Inner thread emoji / symbol text
    # Draw simple '🧵' text or symbol
    try:
        dc.text((18, 14), "🧵", fill=(255, 255, 255, 255))
    except Exception:
        dc.rectangle([20, 20, 44, 44], fill=(255, 255, 255, 255))
        
    return image

def start_fastapi_server():
    """Runs uvicorn FastAPI server in background thread."""
    try:
        uvicorn.run(app, host="127.0.0.1", port=SERVER_PORT, log_level="error")
    except Exception as e:
        print(f"[DesktopApp] Server error: {e}")

def open_dashboard():
    """Opens local dashboard in user's default browser."""
    webbrowser.open(SERVER_URL)

def trigger_threads_scan():
    """Triggers an immediate Threads scan via background API."""
    try:
        requests.post(f"{SERVER_URL}/api/scan", timeout=5)
        print("[DesktopApp] Threads scan triggered via System Tray.")
    except Exception as e:
        print(f"[DesktopApp] Scan trigger error: {e}")

def trigger_pc_login():
    """Triggers local PC Chrome window for visual login."""
    try:
        requests.post(f"{SERVER_URL}/api/browser-login/threads", timeout=5)
        print("[DesktopApp] Chrome login window opened on PC.")
    except Exception as e:
        print(f"[DesktopApp] Login trigger error: {e}")

def exit_app(icon, item):
    """Cleanly stops the desktop app and system tray icon."""
    print("[DesktopApp] Shutting down Meta Threads SEO Bot...")
    icon.stop()
    os._exit(0)

def main():
    print("=" * 60)
    print("Meta Threads Marketing Automation Hub - Windows Desktop App")
    print("=" * 60)
    print(f"[DesktopApp] Starting background server at {SERVER_URL}...")
    
    # 1. Start FastAPI server thread
    server_thread = threading.Thread(target=start_fastapi_server, daemon=True)
    server_thread.start()
    
    # Wait 1.5s for server startup
    time.sleep(1.5)
    
    # 2. Open dashboard in browser on startup
    open_dashboard()
    
def start_tray_icon():
    """Runs System Tray icon in background thread."""
    try:
        import pystray
        from pystray import MenuItem as item
        
        icon_image = create_tray_icon_image()
        
        menu = pystray.Menu(
            item("Open Dashboard Window", lambda: open_dashboard(), default=True),
            item("Login Threads (PC Chrome)", lambda: trigger_pc_login()),
            item("Run Threads Scan Now", lambda: trigger_threads_scan()),
            pystray.Menu.SEPARATOR,
            item("Exit Threads Bot", exit_app)
        )
        
        tray_icon = pystray.Icon("Threads_SEO_Bot", icon_image, "Meta Threads SEO Bot (Running 24/7)", menu)
        print("[DesktopApp] System Tray icon active!")
        tray_icon.run()
    except Exception as e:
        print(f"[DesktopApp] System Tray notice: {e}")

def main():
    print("=" * 60)
    print("Meta Threads Marketing Automation Hub - Windows Desktop App Window")
    print("=" * 60)
    print(f"[DesktopApp] Starting background server at {SERVER_URL}...")
    
    # 1. Start FastAPI server thread
    server_thread = threading.Thread(target=start_fastapi_server, daemon=True)
    server_thread.start()
    
    # Wait 1.5s for server startup
    time.sleep(1.5)
    
    # 2. Start System Tray Icon in background thread
    tray_thread = threading.Thread(target=start_tray_icon, daemon=True)
    tray_thread.start()
    
    # 3. Launch Native Desktop GUI Window using pywebview
    try:
        import webview
        print("[DesktopApp] Launching Desktop GUI Window...")
        window = webview.create_window(
            "🧵 Meta Threads Marketing Automation Hub - Desktop App",
            SERVER_URL,
            width=1300,
            height=880,
            resizable=True,
            min_size=(900, 600)
        )
        webview.start()
    except Exception as e:
        print(f"[DesktopApp] Webview fallback to browser: {e}")
        open_dashboard()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(0)

if __name__ == "__main__":
    main()
