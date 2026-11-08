from __future__ import annotations

import re
import unicodedata


class TextNormalizationService:
    """
    Dedicated service for normalizing resume text without destroying
    critical domain tokens (e.g., C++, .NET, dates, section headers).
    """

    # Replacement mapping for common typographical characters
    CHAR_REPLACEMENTS = {
        "\u00a0": " ",      # Non-breaking space
        "\u200b": "",       # Zero-width space
        "\u200e": "",       # Left-to-right mark
        "\u200f": "",       # Right-to-left mark
        "\u00ad": "",       # Soft hyphen
        "\u2018": "'",      # Left single quote
        "\u2019": "'",      # Right single quote
        "\u201a": "'",      # Single low-9 quote
        "\u201c": '"',      # Left double quote
        "\u201d": '"',      # Right double quote
        "\u201e": '"',      # Double low-9 quote
        "\u2013": "-",      # En dash
        "\u2014": "-",      # Em dash
        "\u2015": "-",      # Horizontal bar
        "\u2022": "• ",     # Bullet
        "\u25cf": "• ",     # Black circle bullet
        "\u25aa": "• ",     # Black small square bullet
        "\u25b8": "• ",     # Black right-pointing small triangle
        "\u2023": "• ",     # Triangular bullet
        "\t": "    ",       # Expand tabs to 4 spaces
    }

    def normalize(self, text: str | None) -> str:
        if not text:
            return ""

        # 1. Unicode normalization (NFKC)
        normalized = unicodedata.normalize("NFKC", text)

        # 2. Character replacements for typography artifacts
        for orig, replacement in self.CHAR_REPLACEMENTS.items():
            normalized = normalized.replace(orig, replacement)

        # 3. Clean carriage returns
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

        # 4. Normalize trailing spaces on lines
        lines = [re.sub(r"[ \t]+$", "", line) for line in normalized.split("\n")]

        # 5. Collapse repeated horizontal spaces (2 or more spaces -> 1 space, but keep bullet indents)
        cleaned_lines = []
        for line in lines:
            # Preserve leading indentation if reasonable, but collapse internal runs of spaces
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append("")
            else:
                collapsed = re.sub(r"[ ]{2,}", " ", stripped)
                cleaned_lines.append(collapsed)

        # 6. Collapse excessive blank lines (max 2 consecutive newlines)
        rejoined = "\n".join(cleaned_lines)
        rejoined = re.sub(r"\n{3,}", "\n\n", rejoined)

        return rejoined.strip()


text_normalizer = TextNormalizationService()

