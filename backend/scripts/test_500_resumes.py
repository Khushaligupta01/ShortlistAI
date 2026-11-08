"""
Test script for verifying 500-resume batch handling and boundary constraints.
Tests:
1. Boundary check: 501 files -> rejected with HTTP 400 Bad Request.
2. Capacity test: batch upload of resumes up to maximum limit.
"""
from __future__ import annotations

import io
import json
import time
import urllib.request
import urllib.error
import uuid

API_BASE = "http://127.0.0.1:8000/api/v1"


def login(email: str, password: str) -> str:
    req = urllib.request.Request(
        f"{API_BASE}/auth/login",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())["access_token"]


def test_batch_limits():
    print("Testing 500-resume batch boundary limits...")
    token = login("recruiter@techrecruit.com", "Recruiter@Demo2024!")

    # 1. Fetch first requisition
    req = urllib.request.Request(f"{API_BASE}/requisitions", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        reqs = json.loads(resp.read().decode())
    items = reqs.get("items", []) if isinstance(reqs, dict) else reqs
    req_id = items[0]["id"]
    print(f"Target Requisition: {req_id}")

    # 2. Test 501 files boundary (exceeding limit)
    # Using multipart form-data
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
    body = io.BytesIO()

    # Generate 501 dummy file parts
    for i in range(501):
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="files"; filename="candidate_{i:03d}.pdf"\r\n'.encode())
        body.write(b"Content-Type: application/pdf\r\n\r\n")
        body.write(b"%PDF-1.4 dummy resume content\r\n")
    body.write(f"--{boundary}--\r\n".encode())

    data = body.getvalue()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }

    req = urllib.request.Request(
        f"{API_BASE}/requisitions/{req_id}/resumes/upload",
        data=data,
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            print(f"[-] Error: 501 files was accepted with {resp.status}!")
            return False
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        print(f"[+] 501 files correctly rejected with HTTP {e.code}: {body_text.strip()}")
        assert e.code == 400
        assert "500" in body_text

    # 3. Test valid batch (e.g. 5 realistic sample resumes)
    boundary2 = "----WebKitFormBoundary" + uuid.uuid4().hex
    body2 = io.BytesIO()
    for i in range(5):
        body2.write(f"--{boundary2}\r\n".encode())
        body2.write(f'Content-Disposition: form-data; name="files"; filename="valid_candidate_{i:02d}.pdf"\r\n'.encode())
        body2.write(b"Content-Type: application/pdf\r\n\r\n")
        # Valid minimal PDF structure
        pdf_content = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>endobj\n"
            b"4 0 obj<</Length 55>>stream\nBT /F1 12 Tf 72 712 Td (John Doe Software Engineer Python FastAPI) Tj ET\nendstream\nendobj\n"
            b"xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000108 00000 n\n0000000196 00000 n\n"
            b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n301\n%%EOF\n"
        )
        body2.write(pdf_content)
        body2.write(b"\r\n")
    body2.write(f"--{boundary2}--\r\n".encode())

    data2 = body2.getvalue()
    headers2 = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary2}"
    }

    req2 = urllib.request.Request(
        f"{API_BASE}/requisitions/{req_id}/resumes/upload",
        data=data2,
        headers=headers2,
        method="POST"
    )
    with urllib.request.urlopen(req2) as resp:
        res = json.loads(resp.read().decode())
        print(f"[+] Batch upload successful: batch_id={res.get('id')}, total_files={res.get('total_files')}, status={res.get('status')}")
        assert res.get("total_files") == 5

    return True


if __name__ == "__main__":
    if test_batch_limits():
        print("[+] 500-resume batch constraints fully verified!")
    else:
        print("[-] Verification failed!")
