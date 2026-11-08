from __future__ import annotations

import pytest

from app.services.text_normalization_service import TextNormalizationService


@pytest.fixture
def normalizer():
    return TextNormalizationService()


def test_collapse_excessive_whitespace(normalizer):
    raw = "Senior   Java     Engineer   \t\twith   8    years\n\n\n\n\nExperience"
    res = normalizer.normalize(raw)
    assert "Senior Java Engineer with 8 years" in res
    assert "\n\n\n" not in res  # Max 2 consecutive newlines


def test_preserve_technical_tokens(normalizer):
    raw = "Skills: C++, C#, .NET, Node.js, Vue.js, PL/SQL, TCP/IP"
    res = normalizer.normalize(raw)
    assert "C++" in res
    assert "C#" in res
    assert ".NET" in res
    assert "Node.js" in res
    assert "PL/SQL" in res


def test_unicode_normalization_and_typography(normalizer):
    # Smart quotes, em-dashes, non-breaking space, soft hyphen
    raw = "“Senior Developer”\u00a0\u2014\u00ad Apex\u2019s Technologies"
    res = normalizer.normalize(raw)
    assert '"Senior Developer"' in res
    assert "Apex's Technologies" in res
    assert "\u00a0" not in res
    assert "\u00ad" not in res


def test_preserve_dates_and_sections(normalizer):
    raw = """
    EMPLOYMENT HISTORY
    Jan 2020 - Present: Lead Engineer
    06/2016 - 12/2019: Software Developer
    """
    res = normalizer.normalize(raw)
    assert "EMPLOYMENT HISTORY" in res
    assert "Jan 2020 - Present: Lead Engineer" in res
    assert "06/2016 - 12/2019: Software Developer" in res

