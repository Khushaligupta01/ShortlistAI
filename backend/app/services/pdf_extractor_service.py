from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

import fitz

logger = logging.getLogger("shortlistai.extraction.pdf")


@dataclass
class PageData:
    page_number: int
    text: str
    char_count: int


@dataclass
class PDFExtractionResult:
    success: bool
    status: str  # "extracted", "ocr_required", "empty_pdf", "encrypted_pdf", "corrupted_pdf", "failed"
    raw_text: str
    page_count: int
    pages: List[PageData] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


class PDFExtractorService:
    """PDF document text extraction using PyMuPDF (fitz)."""

    def extract_text(self, content: bytes) -> PDFExtractionResult:
        doc = None
        try:
            doc = fitz.open(stream=content, filetype="pdf")

            if doc.is_encrypted:
                return PDFExtractionResult(
                    success=False,
                    status="encrypted_pdf",
                    raw_text="",
                    page_count=0,
                    error_code="ENCRYPTED_PDF",
                    error_message="PDF is password-protected or encrypted.",
                )

            page_count = len(doc)
            if page_count == 0:
                return PDFExtractionResult(
                    success=False,
                    status="empty_pdf",
                    raw_text="",
                    page_count=0,
                    error_code="EMPTY_PDF",
                    error_message="PDF contains no pages.",
                )

            pages: List[PageData] = []
            full_text_chunks: List[str] = []
            total_clean_chars = 0

            for idx in range(page_count):
                page = doc[idx]
                page_text = page.get_text("text") or ""
                stripped = page_text.strip()
                total_clean_chars += len(stripped)

                pages.append(
                    PageData(
                        page_number=idx + 1,
                        text=page_text,
                        char_count=len(page_text),
                    )
                )

                if page_text:
                    if page_count > 1:
                        full_text_chunks.append(f"--- Page {idx + 1} ---\n{page_text}")
                    else:
                        full_text_chunks.append(page_text)

            combined_text = "\n\n".join(full_text_chunks)

            # Check if PDF contains extractable text or is a scanned image
            # If average chars per page < 15 or total non-whitespace chars < 20, mark OCR_REQUIRED
            if total_clean_chars < 20:
                return PDFExtractionResult(
                    success=False,
                    status="ocr_required",
                    raw_text=combined_text,
                    page_count=page_count,
                    pages=pages,
                    error_code="OCR_REQUIRED",
                    error_message="Document appears to be a scanned image or contains no extractable text. OCR is required.",
                )

            return PDFExtractionResult(
                success=True,
                status="extracted",
                raw_text=combined_text,
                page_count=page_count,
                pages=pages,
            )

        except fitz.FileDataError as e:
            return PDFExtractionResult(
                success=False,
                status="corrupted_pdf",
                raw_text="",
                page_count=0,
                error_code="CORRUPTED_PDF",
                error_message=f"PDF data is corrupted or cannot be parsed: {e}",
            )
        except Exception as e:
            logger.exception("Unexpected error during PDF extraction")
            return PDFExtractionResult(
                success=False,
                status="failed",
                raw_text="",
                page_count=0,
                error_code="EXTRACTION_FAILED",
                error_message=f"Failed to extract text from PDF: {str(e)}",
            )
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass


pdf_extractor = PDFExtractorService()

