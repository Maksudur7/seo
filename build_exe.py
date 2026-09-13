import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def build_executable():
    print("=" * 60)
    print("[Build] Compiling Meta Threads SEO Bot into Windows Executable (.exe)")
    print("=" * 60)
    
    python_exe = sys.executable
    
    cmd = [
        python_exe, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed", # Hide black console window, runs silently in System Tray
        "--name=Threads_SEO_Bot",
        "--add-data", f"{BASE_DIR / 'templates'};templates",
        "--add-data", f"{BASE_DIR / 'static'};static",
        "--add-data", f"{BASE_DIR / 'modules'};modules",
        "--add-data", f"{BASE_DIR / 'data'};data",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=pystray",
        "--hidden-import=PIL",
        "--hidden-import=playwright",
        "--hidden-import=jinja2",
        "--hidden-import=google.genai",
        "--hidden-import=feedparser",
        "--hidden-import=bs4",
        str(BASE_DIR / "desktop_app.py")
    ]
    
    print(f"[Build] Running PyInstaller...")
    res = subprocess.run(cmd, cwd=str(BASE_DIR))
    
    if res.returncode == 0:
        dist_folder = BASE_DIR / "dist" / "Threads_SEO_Bot"
        exe_path = dist_folder / "Threads_SEO_Bot.exe"
        print("=" * 60)
        print(f"[Build] BUILD SUCCESSFUL!")
        print(f"[Build] Executable Folder: {dist_folder}")
        print(f"[Build] Executable Path: {exe_path}")
        print("=" * 60)
    else:
        print("[Build] Build failed with return code:", res.returncode)

if __name__ == "__main__":
    build_executable()
