"""
Automated genuine screenshot capture script for ShortlistAI (Phase 10 Release).
Spins up local servers, uses Microsoft Edge headless to capture real UI screens,
and saves genuine high-resolution PNGs to docs/submission/screenshots/.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
import json

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "submission", "screenshots"))

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


def capture_screenshot(url: str, filename: str) -> None:
    dest = os.path.join(OUTPUT_DIR, filename)
    cmd = [
        EDGE_PATH,
        "--headless=new",
        "--disable-gpu",
        "--window-size=1440,900",
        "--virtual-time-budget=6000",
        f"--screenshot={dest}",
        url,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(dest) and os.path.getsize(dest) > 1000:
            print(f"  [+] Captured: {filename} ({os.path.getsize(dest) // 1024} KB)")
        else:
            print(f"  [-] Failed or empty: {filename}")
    except Exception as e:
        print(f"  [-] Error capturing {filename}: {e}")


def main():
    print("==================================================")
    print("   ShortlistAI Genuine UI Screenshot Capture      ")
    print("==================================================")

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")

    # Start Backend
    print("[1/4] Starting FastAPI backend on port 8000...")
    python_exe = sys.executable
    venv_py = os.path.join(backend_dir, ".venv310", "Scripts", "python.exe")
    if os.path.exists(venv_py):
        python_exe = venv_py

    backend_proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=backend_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Start Frontend
    print("[2/4] Starting Next.js frontend on port 3000...")
    frontend_proc = subprocess.Popen(
        "npm run start -- -p 3000",
        cwd=frontend_dir,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        if not wait_for_url("http://127.0.0.1:8000/api/v1/health", timeout=30):
            print("[-] Backend failed to start on http://127.0.0.1:8000")
            return

        if not wait_for_url("http://127.0.0.1:3000", timeout=45):
            print("[-] Frontend failed to start on http://127.0.0.1:3000")
            return

        print("[+] Both servers healthy and accepting requests!")

        # Query dynamic entity IDs for deep-link screenshots
        recruiter_token = ""
        client_token = ""
        req_id = ""
        cand_id = ""
        sub_id = ""

        # Authenticate Recruiter
        try:
            req_data = json.dumps({"email": "recruiter@techrecruit.com", "password": "Recruiter@Demo2024!"}).encode("utf-8")
            req = urllib.request.Request("http://127.0.0.1:8000/api/v1/auth/login", data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                recruiter_token = json.loads(resp.read().decode())["access_token"]
        except Exception as e:
            print(f"[-] Recruiter login failed: {e}")

        # Authenticate Client
        try:
            req_data = json.dumps({"email": "client@acme.com", "password": "Client@Demo2024!"}).encode("utf-8")
            req = urllib.request.Request("http://127.0.0.1:8000/api/v1/auth/login", data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                client_token = json.loads(resp.read().decode())["access_token"]
        except Exception as e:
            print(f"[-] Client login failed: {e}")

        # Discover dynamic entities
        if recruiter_token:
            auth_headers = {"Authorization": f"Bearer {recruiter_token}"}
            try:
                req_list_req = urllib.request.Request("http://127.0.0.1:8000/api/v1/requisitions", headers=auth_headers)
                with urllib.request.urlopen(req_list_req) as resp:
                    reqs = json.loads(resp.read().decode())
                    if reqs:
                        req_id = reqs[0]["id"]
            except Exception as e:
                print(f"[*] Requisition lookup: {e}")

            try:
                cand_list_req = urllib.request.Request("http://127.0.0.1:8000/api/v1/candidates", headers=auth_headers)
                with urllib.request.urlopen(cand_list_req) as resp:
                    cands = json.loads(resp.read().decode())["items"]
                    if cands:
                        cand_id = cands[0]["id"]
            except Exception as e:
                print(f"[*] Candidate lookup: {e}")

            try:
                pipeline_req = urllib.request.Request("http://127.0.0.1:8000/api/v1/recruiter/pipeline", headers=auth_headers)
                with urllib.request.urlopen(pipeline_req) as resp:
                    board = json.loads(resp.read().decode())
                    if board.get("submissions"):
                        sub_id = board["submissions"][0]["submission_id"]
            except Exception as e:
                print(f"[*] Pipeline lookup: {e}")

        # Capture Screens
        print("\n[3/4] Capturing genuine application screenshots...")

        screens = [
            ("01_login.png", "http://127.0.0.1:3000/login"),
            ("02_recruiter_dashboard.png", f"http://127.0.0.1:3000/dashboard?auth_token={recruiter_token}"),
            ("03_requisition_workspace.png", f"http://127.0.0.1:3000/requisitions?auth_token={recruiter_token}"),
            ("04_scorecard_editor.png", f"http://127.0.0.1:3000/requisitions/new?auth_token={recruiter_token}"),
            ("05_ranked_candidates.png", f"http://127.0.0.1:3000/candidates?auth_token={recruiter_token}"),
            ("06_hiring_pipeline.png", f"http://127.0.0.1:3000/pipeline?auth_token={recruiter_token}"),
            ("07_client_dashboard.png", f"http://127.0.0.1:3000/client?auth_token={client_token}"),
            ("08_client_submissions.png", f"http://127.0.0.1:3000/client/submissions?auth_token={client_token}"),
            ("09_privacy_dashboard.png", f"http://127.0.0.1:3000/privacy?auth_token={recruiter_token}"),
            ("10_audit_governance.png", f"http://127.0.0.1:3000/governance?auth_token={recruiter_token}"),
        ]

        if req_id:
            screens.append(("11_resume_upload_workspace.png", f"http://127.0.0.1:3000/requisitions/{req_id}?auth_token={recruiter_token}"))
        if cand_id:
            screens.append(("12_candidate_evidence_details.png", f"http://127.0.0.1:3000/candidates/{cand_id}?auth_token={recruiter_token}"))
        if sub_id:
            screens.append(("13_client_candidate_review.png", f"http://127.0.0.1:3000/client/submissions/{sub_id}?auth_token={client_token}"))

        for filename, url in screens:
            capture_screenshot(url, filename)

    finally:
        print("\n[4/4] Tearing down background servers...")
        try:
            backend_proc.terminate()
            backend_proc.kill()
        except Exception:
            pass

        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        print("[+] Screenshot capture completed successfully!")


if __name__ == "__main__":
    main()
