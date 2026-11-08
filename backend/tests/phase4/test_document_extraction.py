from __future__ import annotations

from pathlib import Path

import pytest

from app.services.docx_extractor_service import DocxExtractorService
from app.services.pdf_extractor_service import PDFExtractorService

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "resumes"


@pytest.fixture
def pdf_service():
    return PDFExtractorService()


@pytest.fixture
def docx_service():
    return DocxExtractorService()


def test_pdf_extraction_normal(pdf_service):
    content = (FIXTURES_DIR / "01_strong_java_senior.pdf").read_bytes()
    res = pdf_service.extract_text(content)
    assert res.success is True
    assert res.status == "extracted"
    assert res.page_count == 1
    assert "Aarav Sharma" in res.raw_text
    assert "Spring Boot" in res.raw_text
    assert "Stanford University" in res.raw_text


def test_pdf_extraction_multipage(pdf_service):
    content = (FIXTURES_DIR / "11_multipage_java_lead.pdf").read_bytes()
    res = pdf_service.extract_text(content)
    assert res.success is True
    assert res.page_count == 3
    assert len(res.pages) == 3
    assert "Hannah Abbott" in res.raw_text
    assert "Columbia University" in res.raw_text
    assert "AWS Certified Solutions Architect" in res.raw_text


def test_pdf_scanned_ocr_required(pdf_service):
    content = (FIXTURES_DIR / "13_scanned_image_ocr_required.pdf").read_bytes()
    res = pdf_service.extract_text(content)
    assert res.success is False
    assert res.status == "ocr_required"
    assert res.error_code == "OCR_REQUIRED"
    assert "OCR is required" in res.error_message


def test_docx_extraction_paragraphs(docx_service):
    content = (FIXTURES_DIR / "02_partial_java_developer.docx").read_bytes()
    res = docx_service.extract_text(content)
    assert res.success is True
    assert res.status == "extracted"
    assert "Bhavna Patel" in res.raw_text
    assert "Innovate Corp" in res.raw_text
    assert res.paragraph_count > 0


def test_docx_extraction_tables(docx_service):
    content = (FIXTURES_DIR / "10_docx_with_tables.docx").read_bytes()
    res = docx_service.extract_text(content)
    assert res.success is True
    assert res.table_count >= 2
    assert "George Vance" in res.raw_text
    assert "Peak Technologies" in res.raw_text
    assert "Colorado State University" in res.raw_text


def test_pdf_corrupted_handling(pdf_service):
    content = (FIXTURES_DIR / "08_malformed.pdf").read_bytes()
    res = pdf_service.extract_text(content)
    assert res.success is False
    assert res.status in ("corrupted_pdf", "failed")
    assert res.error_code is not None
