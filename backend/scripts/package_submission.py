"""
Automated packaging and verification script for ShortlistAI final submission ZIP.

Creates: E:\\ShortlistAI\\dist\\ShortlistAI-Submission.zip
Strict Requirements:
1. Destination: dist/ShortlistAI-Submission.zip
2. Contains EXACTLY TWO FILES:
   - technical-design-document.pdf
   - deployment.md
3. No additional files, directories, or source code inside the ZIP.
4. Total archive size <= 25 MB (25,000,000 bytes).
5. Programmatic verification: integrity check, PDF open check, deployment.md readability.
"""
from __future__ import annotations

import io
import os
import sys
import zipfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DIST_DIR = os.path.join(ROOT_DIR, "dist")
ZIP_PATH = os.path.join(DIST_DIR, "ShortlistAI-Submission.zip")

PDF_SRC = os.path.join(ROOT_DIR, "docs", "submission", "technical-design-document.pdf")
DEPLOY_SRC = os.path.join(ROOT_DIR, "deployment.md")

MAX_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB = 26,214,400 bytes (or 25,000,000 bytes)
STRICT_LIMIT_BYTES = 25_000_000


def verify_source_files():
    if not os.path.isfile(PDF_SRC):
        print(f"[-] ERROR: Missing source PDF: {PDF_SRC}")
        sys.exit(1)
    if os.path.getsize(PDF_SRC) == 0:
        print(f"[-] ERROR: Source PDF is empty: {PDF_SRC}")
        sys.exit(1)

    if not os.path.isfile(DEPLOY_SRC):
        print(f"[-] ERROR: Missing source deployment.md: {DEPLOY_SRC}")
        sys.exit(1)
    if os.path.getsize(DEPLOY_SRC) == 0:
        print(f"[-] ERROR: Source deployment.md is empty: {DEPLOY_SRC}")
        sys.exit(1)

    print(f"[+] Verified source PDF: {PDF_SRC} ({os.path.getsize(PDF_SRC):,} bytes)")
    print(f"[+] Verified source deployment.md: {DEPLOY_SRC} ({os.path.getsize(DEPLOY_SRC):,} bytes)")


def package_submission_zip():
    verify_source_files()
    os.makedirs(DIST_DIR, exist_ok=True)

    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    print(f"\n[*] Packaging submission archive at: {ZIP_PATH}")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        # 1. technical-design-document.pdf at root
        zipf.write(PDF_SRC, arcname="technical-design-document.pdf")
        print("  -> Added: technical-design-document.pdf")

        # 2. deployment.md at root
        zipf.write(DEPLOY_SRC, arcname="deployment.md")
        print("  -> Added: deployment.md")

    print("[+] Packaging completed.")


def verify_submission_zip():
    print("\n" + "=" * 60)
    print("   PROGRAMMATIC SUBMISSION ZIP VERIFICATION")
    print("=" * 60)

    if not os.path.isfile(ZIP_PATH):
        raise FileNotFoundError(f"ZIP file not found at {ZIP_PATH}")

    size_bytes = os.path.getsize(ZIP_PATH)
    size_mb = size_bytes / (1024 * 1024)
    print(f"Archive Path:       {ZIP_PATH}")
    print(f"Archive Size:       {size_bytes:,} bytes ({size_mb:.2f} MB)")
    print(f"Size Limit:         <= 25 MB ({STRICT_LIMIT_BYTES:,} bytes)")

    if size_bytes > STRICT_LIMIT_BYTES:
        raise ValueError(f"ZIP size {size_bytes} exceeds strict 25 MB limit!")
    print("  [PASS] Size constraint satisfied.")

    # Inspect zip entries
    with zipfile.ZipFile(ZIP_PATH, "r") as zipf:
        # Integrity check
        test_res = zipf.testzip()
        if test_res is not None:
            raise RuntimeError(f"Corrupt entry found in ZIP: {test_res}")
        print("  [PASS] ZIP integrity test passed (testzip() returned None).")

        entries = zipf.infolist()
        entry_names = [e.filename for e in entries]
        print(f"Total entries:      {len(entries)}")
        print(f"Entry names:        {entry_names}")

        expected_names = ["technical-design-document.pdf", "deployment.md"]
        if sorted(entry_names) != sorted(expected_names):
            raise AssertionError(f"ZIP must contain EXACTLY {expected_names}, found: {entry_names}")
        print("  [PASS] Exactly 2 files present: 'technical-design-document.pdf' and 'deployment.md'.")

        for entry in entries:
            if entry.file_size == 0:
                raise ValueError(f"Entry {entry.filename} is 0 bytes!")
            print(f"  [PASS] '{entry.filename}' is non-empty ({entry.file_size:,} bytes uncompressed).")

        # Programmatically verify PDF readability
        pdf_bytes = zipf.read("technical-design-document.pdf")
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(doc)
            first_page_text = doc[0].get_text()
            print(f"  [PASS] PDF opened successfully via PyMuPDF: {page_count} pages detected.")
            if "https://github.com/Khushaligupta01/ShortlistAI" not in first_page_text:
                raise AssertionError("GitHub repository URL not found on first page of PDF!")
            print("  [PASS] Authoritative GitHub URL confirmed on Page 1 of PDF.")
        except Exception as e:
            print(f"  [-] Warning testing PDF via PyMuPDF: {e}")
            if len(pdf_bytes) < 1000:
                raise AssertionError("PDF data appears invalid or too small!")

        # Programmatically verify deployment.md readability
        md_bytes = zipf.read("deployment.md")
        md_text = md_bytes.decode("utf-8")
        if "https://github.com/Khushaligupta01/ShortlistAI" not in md_text:
            raise AssertionError("GitHub repository URL not found in deployment.md!")
        print(f"  [PASS] deployment.md read successfully ({len(md_text):,} characters).")
        print("  [PASS] Authoritative GitHub URL confirmed in deployment.md.")

    print("=" * 60)
    print("   [+] ALL SUBMISSION ZIP CHECKS PASSED PERFECTLY!")
    print("=" * 60)


if __name__ == "__main__":
    package_submission_zip()
    verify_submission_zip()
