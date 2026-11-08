"""
Responsive viewport audit and screenshot capture for ShortlistAI.
Captures genuine UI across Desktop (1440x900), Laptop (1280x800), Tablet (768x1024), and Mobile (390x844).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
import json

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "final-audit", "screenshots"))

os.makedirs(OUTPUT_DIR, exist_ok=True)


def wait_for_url(url: str, timeout: int = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def capture_viewport(url: str, width: int, height: int, filename: str) -> None:
    dest = os.path.join(OUTPUT_DIR, filename)
    cmd = [
        EDGE_PATH,
        "--headless=new",
        "--disable-gpu",
        f"--window-size={width},{height}",
        "--virtual-time-budget=5000",
        f"--screenshot={dest}",
        url,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(dest) and os.path.getsize(dest) > 1000:
            print(f"  [+] Captured {filename} ({width}x{height}): {os.path.getsize(dest) // 1024} KB")
        else:
            print(f"  [-] Failed or empty: {filename}")
    except Exception as e:
        print(f"  [-] Error capturing {filename}: {e}")


def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")

    print("[1/3] Starting backend & frontend...")
    b_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=backend_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    f_proc = subprocess.Popen(
        "npm run start -- -p 3000",
        cwd=frontend_dir,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        if not wait_for_url("http://127.0.0.1:8000/api/v1/health", 30) or not wait_for_url("http://127.0.0.1:3000", 45):
            print("[-] Server startup failed.")
            return

        # Login
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/v1/auth/login",
            data=json.dumps({"email": "recruiter@techrecruit.com", "password": "Recruiter@Demo2024!"}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            token = json.loads(resp.read().decode())["access_token"]

        print("[2/3] Capturing responsive viewports...")
        viewports = [
            ("Desktop", 1440, 900, "desktop_1440x900_dashboard.png", f"http://127.0.0.1:3000/dashboard?auth_token={token}"),
            ("Laptop", 1280, 800, "laptop_1280x800_dashboard.png", f"http://127.0.0.1:3000/dashboard?auth_token={token}"),
            ("Tablet", 768, 1024, "tablet_768x1024_dashboard.png", f"http://127.0.0.1:3000/dashboard?auth_token={token}"),
            ("Mobile", 390, 844, "mobile_390x844_dashboard.png", f"http://127.0.0.1:3000/dashboard?auth_token={token}"),
            ("Mobile Pipeline", 390, 844, "mobile_390x844_pipeline.png", f"http://127.0.0.1:3000/pipeline?auth_token={token}"),
            ("Mobile Login", 390, 844, "mobile_390x844_login.png", "http://127.0.0.1:3000/login"),
        ]

        for name, w, h, fname, url in viewports:
            capture_viewport(url, w, h, fname)

    finally:
        print("[3/3] Shutting down...")
        try:
            b_proc.terminate()
            b_proc.kill()
        except Exception:
            pass
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(f_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


if __name__ == "__main__":
    main()
