"""
Automated packaging script for ShortlistAI final submission package.
Creates dist/ShortlistAI-Submission.zip strictly under 25 MB, excluding all
version control metadata, virtual environments, build artifacts, node_modules,
temporary files, and environment secrets.
"""
from __future__ import annotations

import os
import sys
import zipfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DIST_DIR = os.path.join(ROOT_DIR, "dist")
ZIP_PATH = os.path.join(DIST_DIR, "ShortlistAI-Submission.zip")

EXCLUDED_DIRS = {
    ".git",
    ".github_temp",
    ".venv",
    ".venv310",
    "venv",
    "env",
    "node_modules",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "storage",
    "tmp",
    "coverage",
    ".kiro",
}

EXCLUDED_FILES = {
    ".env",
    ".env.local",
    ".env.development",
    "tsconfig.tsbuildinfo",
}

EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".log",
}


def should_include(rel_path: str) -> bool:
    parts = rel_path.replace("\\", "/").split("/")
    # Check directory exclusions
    for part in parts[:-1]:
        if part in EXCLUDED_DIRS:
            return False

    filename = parts[-1]
    if filename in EXCLUDED_FILES:
        return False

    # Never include secrets or local env files
    if filename.startswith(".env") and not filename.endswith(".example"):
        return False

    _, ext = os.path.splitext(filename)
    if ext.lower() in EXCLUDED_EXTENSIONS:
        return False

    return True


def package_submission():
    os.makedirs(DIST_DIR, exist_ok=True)
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    print(f"Creating submission package at: {ZIP_PATH}")
    file_count = 0

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(ROOT_DIR):
            # Prune excluded directories in-place for fast traversal
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, ROOT_DIR)

                if should_include(rel_path):
                    zipf.write(abs_path, rel_path)
                    file_count += 1

    size_bytes = os.path.getsize(ZIP_PATH)
    size_mb = size_bytes / (1024 * 1024)

    print("==================================================")
    print("   ShortlistAI Final Submission Package Summary   ")
    print("==================================================")
    print(f"  Target File:     {ZIP_PATH}")
    print(f"  Total Files:     {file_count} files archived")
    print(f"  Package Size:    {size_mb:.2f} MB ({size_bytes} bytes)")
    print(f"  Size Limit:      25.00 MB")
    print(f"  Status:          {'PASSED (Compliant)' if size_mb < 25.0 else 'FAILED (Exceeds 25 MB)'}")
    print("==================================================")

    if size_mb >= 25.0:
        print("[-] Error: Submission package exceeds 25 MB limit!")
        sys.exit(1)


if __name__ == "__main__":
    package_submission()
