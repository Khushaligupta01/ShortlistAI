from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.services.document_validation_service import DocumentValidationService

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "resumes"


@pytest.fixture
def validator():
    return DocumentValidationService(max_file_size_bytes=5 * 1024 * 1024)  # 5 MB test limit


def test_valid_pdf_validation(validator):
    pdf_bytes = (FIXTURES_DIR / "01_strong_java_senior.pdf").read_bytes()
    res = validator.validate_file("01_strong_java_senior.pdf", pdf_bytes, "application/pdf")
    assert res.is_valid is True
    assert res.error_code is None
    assert res.detected_mime == "application/pdf"
    assert res.file_size_bytes > 0
    assert len(res.sha256_hash) == 64


def test_valid_docx_validation(validator):
    docx_bytes = (FIXTURES_DIR / "02_partial_java_developer.docx").read_bytes()
    res = validator.validate_file(
        "02_partial_java_developer.docx",
        docx_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert res.is_valid is True
    assert res.error_code is None
    assert "wordprocessingml" in res.detected_mime
    assert res.file_size_bytes > 0


def test_unsupported_extension(validator):
    res = validator.validate_file("script.py", b"print('hello')", "text/x-python")
    assert res.is_valid is False
    assert res.error_code == "UNSUPPORTED_EXTENSION"
    assert "not supported" in res.error_message_safe


def test_spoofed_pdf_signature(validator):
    # A text file renamed as .pdf
    fake_pdf = b"This is just plain text masquerading as a PDF file."
    res = validator.validate_file("resume.pdf", fake_pdf, "application/pdf")
    assert res.is_valid is False
    assert res.error_code == "INVALID_SIGNATURE"
    assert "header signature" in res.error_message_safe


def test_spoofed_docx_signature(validator):
    # Plain text renamed as .docx
    fake_docx = b"This is plain text with a fake .docx extension."
    res = validator.validate_file("resume.docx", fake_docx)
    assert res.is_valid is False
    assert res.error_code == "INVALID_SIGNATURE"


def test_empty_file(validator):
    res = validator.validate_file("empty.pdf", b"")
    assert res.is_valid is False
    assert res.error_code == "EMPTY_FILE"
    assert res.file_size_bytes == 0


def test_oversized_file(validator):
    # Validator has 5MB limit; create 6MB buffer
    large_bytes = b"A" * (6 * 1024 * 1024)
    res = validator.validate_file("large.pdf", large_bytes, "application/pdf")
    assert res.is_valid is False
    assert res.error_code == "FILE_TOO_LARGE"
    assert "exceeds maximum allowed size" in res.error_message_safe


def test_malformed_pdf(validator):
    malformed_bytes = (FIXTURES_DIR / "08_malformed.pdf").read_bytes()
    res = validator.validate_file("08_malformed.pdf", malformed_bytes)
    assert res.is_valid is False
    assert res.error_code in ("CORRUPTED_PDF", "INVALID_SIGNATURE")


def test_malformed_docx(validator):
    import zipfile

    # Create a zip without word/document.xml
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        zf.writestr("test.txt", "hello")
    res = validator.validate_file("bad.docx", bio.getvalue())
    assert res.is_valid is False
    assert res.error_code == "MALFORMED_DOCX"
