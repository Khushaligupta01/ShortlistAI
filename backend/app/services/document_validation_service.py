from __future__ import annotations

import hashlib
import io
import mimetypes
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
PDF_MIMES = {"application/pdf", "application/x-pdf"}
DOCX_MIMES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",
}


@dataclass
class ValidationResult:
    is_valid: bool
    error_code: str | None
    error_message_safe: str | None
    detected_mime: str
    file_size_bytes: int
    sha256_hash: str


class DocumentValidationService:
    """Strict validation for uploaded resume documents."""

    def __init__(
        self,
        max_file_size_bytes: int | None = None,
    ) -> None:
        self.max_file_size_bytes = max_file_size_bytes or settings.MAX_RESUME_FILE_SIZE_BYTES

    def compute_sha256(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def validate_file(
        self,
        filename: str,
        content: bytes,
        client_mime: str | None = None,
    ) -> ValidationResult:
        file_size = len(content)
        sha256_hash = self.compute_sha256(content)

        # 1. Check empty file
        if file_size == 0:
            return ValidationResult(
                is_valid=False,
                error_code="EMPTY_FILE",
                error_message_safe="Uploaded file is empty (0 bytes).",
                detected_mime="application/octet-stream",
                file_size_bytes=0,
                sha256_hash=sha256_hash,
            )

        # 2. Check maximum size limit
        if file_size > self.max_file_size_bytes:
            max_mb = self.max_file_size_bytes / (1024 * 1024)
            return ValidationResult(
                is_valid=False,
                error_code="FILE_TOO_LARGE",
                error_message_safe=f"File exceeds maximum allowed size of {max_mb:.1f} MB.",
                detected_mime=client_mime or "application/octet-stream",
                file_size_bytes=file_size,
                sha256_hash=sha256_hash,
            )

        # 3. Check file extension
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return ValidationResult(
                is_valid=False,
                error_code="UNSUPPORTED_EXTENSION",
                error_message_safe=f"File extension '{ext}' is not supported. Allowed: .pdf, .docx",
                detected_mime=client_mime or "application/octet-stream",
                file_size_bytes=file_size,
                sha256_hash=sha256_hash,
            )

        # 4. Check file magic / signature & structural validity
        if ext == ".pdf":
            return self._validate_pdf(content, sha256_hash, file_size)
        elif ext == ".docx":
            return self._validate_docx(content, sha256_hash, file_size)

        return ValidationResult(
            is_valid=False,
            error_code="UNSUPPORTED_EXTENSION",
            error_message_safe="Unsupported file format.",
            detected_mime="application/octet-stream",
            file_size_bytes=file_size,
            sha256_hash=sha256_hash,
        )

    def _validate_pdf(self, content: bytes, sha256_hash: str, file_size: int) -> ValidationResult:
        # Check PDF header magic bytes (%PDF) within first 1024 bytes
        header = content[:1024]
        if b"%PDF-" not in header and not header.lstrip().startswith(b"%PDF"):
            return ValidationResult(
                is_valid=False,
                error_code="INVALID_SIGNATURE",
                error_message_safe="File content does not match standard PDF header signature.",
                detected_mime="application/octet-stream",
                file_size_bytes=file_size,
                sha256_hash=sha256_hash,
            )

        # Check structural opening with PyMuPDF
        try:
            import fitz

            doc = fitz.open(stream=content, filetype="pdf")
            if doc.is_encrypted:
                doc.close()
                return ValidationResult(
                    is_valid=False,
                    error_code="ENCRYPTED_PDF",
                    error_message_safe="Password-protected or encrypted PDFs cannot be processed.",
                    detected_mime="application/pdf",
                    file_size_bytes=file_size,
                    sha256_hash=sha256_hash,
                )

            page_count = len(doc)
            doc.close()

            if page_count == 0:
                return ValidationResult(
                    is_valid=False,
                    error_code="EMPTY_PDF",
                    error_message_safe="PDF contains no readable pages.",
                    detected_mime="application/pdf",
                    file_size_bytes=file_size,
                    sha256_hash=sha256_hash,
                )

            return ValidationResult(
                is_valid=True,
                error_code=None,
                error_message_safe=None,
                detected_mime="application/pdf",
                file_size_bytes=file_size,
                sha256_hash=sha256_hash,
            )
        except Exception:
            return ValidationResult(
                is_valid=False,
                error_code="CORRUPTED_PDF",
                error_message_safe="Corrupted or malformed PDF structure.",
                detected_mime="application/pdf",
                file_size_bytes=file_size,
                sha256_hash=sha256_hash,
            )

    def _validate_docx(self, content: bytes, sha256_hash: str, file_size: int) -> ValidationResult:
        # Check ZIP magic bytes (PK\x03\x04)
        if not content.startswith(b"PK\x03\x04"):
            return ValidationResult(
                is_valid=False,
                error_code="INVALID_SIGNATURE",
                error_message_safe="File content does not match DOCX package signature.",
                detected_mime="application/octet-stream",
                file_size_bytes=file_size,
                sha256_hash=sha256_hash,
            )

        # Check internal DOCX structure (word/document.xml)
        try:
            bio = io.BytesIO(content)
            with zipfile.ZipFile(bio, "r") as zf:
                namelist = zf.namelist()
                if "word/document.xml" not in namelist:
                    return ValidationResult(
                        is_valid=False,
                        error_code="MALFORMED_DOCX",
                        error_message_safe="Archive is missing valid DOCX document structure (word/document.xml).",
                        detected_mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        file_size_bytes=file_size,
                        sha256_hash=sha256_hash,
                    )

            # Test opening with python-docx
            import docx
            doc = docx.Document(io.BytesIO(content))

            return ValidationResult(
                is_valid=True,
                error_code=None,
                error_message_safe=None,
                detected_mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                file_size_bytes=file_size,
                sha256_hash=sha256_hash,
            )
        except Exception:
            return ValidationResult(
                is_valid=False,
                error_code="CORRUPTED_DOCX",
                error_message_safe="Corrupted or malformed DOCX structure.",
                detected_mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                file_size_bytes=file_size,
                sha256_hash=sha256_hash,
            )


validation_service = DocumentValidationService()
