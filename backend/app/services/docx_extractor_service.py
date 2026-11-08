from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import List

import docx

logger = logging.getLogger("shortlistai.extraction.docx")


@dataclass
class DocxExtractionResult:
    success: bool
    status: str  # "extracted", "empty_docx", "corrupted_docx", "failed"
    raw_text: str
    paragraph_count: int
    table_count: int
    error_code: str | None = None
    error_message: str | None = None


class DocxExtractorService:
    """DOCX document text extraction using python-docx."""

    def extract_text(self, content: bytes) -> DocxExtractionResult:
        try:
            bio = io.BytesIO(content)
            doc = docx.Document(bio)

            text_blocks: List[str] = []

            # 1. Extract headers (from header parts if any)
            headers_seen = set()
            for section in doc.sections:
                try:
                    header = section.header
                    if header and not header.is_linked_to_previous:
                        for p in header.paragraphs:
                            t = p.text.strip()
                            if t and t not in headers_seen:
                                headers_seen.add(t)
                                text_blocks.append(f"[Header: {t}]")
                except Exception:
                    pass

            # 2. Extract paragraphs
            paragraph_count = 0
            for p in doc.paragraphs:
                p_text = p.text.strip()
                if p_text:
                    text_blocks.append(p_text)
                    paragraph_count += 1

            # 3. Extract tables
            table_count = len(doc.tables)
            for t_idx, table in enumerate(doc.tables, 1):
                table_lines: List[str] = []
                for row in table.rows:
                    # Clean and join cells
                    cell_texts = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    # Deduplicate repeated merged cell text in same row
                    deduped_cells = []
                    for c in cell_texts:
                        if not deduped_cells or c != deduped_cells[-1]:
                            deduped_cells.append(c)
                    row_line = " | ".join(c for c in deduped_cells if c)
                    if row_line:
                        table_lines.append(row_line)

                if table_lines:
                    text_blocks.append("\n".join(table_lines))

            # 4. Extract footers if useful
            footers_seen = set()
            for section in doc.sections:
                try:
                    footer = section.footer
                    if footer and not footer.is_linked_to_previous:
                        for p in footer.paragraphs:
                            t = p.text.strip()
                            if t and t not in footers_seen:
                                footers_seen.add(t)
                                text_blocks.append(f"[Footer: {t}]")
                except Exception:
                    pass

            combined_text = "\n\n".join(text_blocks).strip()

            if not combined_text:
                return DocxExtractionResult(
                    success=False,
                    status="empty_docx",
                    raw_text="",
                    paragraph_count=0,
                    table_count=table_count,
                    error_code="EMPTY_DOCX",
                    error_message="DOCX document contains no readable text or tables.",
                )

            return DocxExtractionResult(
                success=True,
                status="extracted",
                raw_text=combined_text,
                paragraph_count=paragraph_count,
                table_count=table_count,
            )

        except Exception as e:
            logger.exception("Error extracting text from DOCX")
            return DocxExtractionResult(
                success=False,
                status="corrupted_docx",
                raw_text="",
                paragraph_count=0,
                table_count=0,
                error_code="CORRUPTED_DOCX",
                error_message=f"Failed to read DOCX document: {str(e)}",
            )


docx_extractor = DocxExtractorService()
