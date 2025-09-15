"""
Email Litigation Risk Analyzer

This module provides functions for scanning email content for language
that could trigger litigation risk flags. It exports a single
convenience function, `analyze_email`, which accepts a dictionary
representing a single email and returns a structured result with a
risk score, risk categories, count of flags, and snippets from the
email that triggered each flag.

Note: This is a heuristic, rule‑based analyzer and not a substitute
for legal counsel. It is intended to help triage emails for further
review by qualified professionals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Pattern, Tuple


@dataclass
class RiskPattern:
    """Represents a risk category and its associated regex patterns."""

    category: str
    patterns: List[Pattern[str]]

    def match(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Return a list of matches (snippet, start, end) for all regexes in this
        category within the provided text.
        """
        matches = []
        for regex in self.patterns:
            for m in regex.finditer(text):
                # Capture a snippet around the match for context
                start, end = m.start(), m.end()
                snippet_start = max(0, start - 40)
                snippet_end = min(len(text), end + 40)
                snippet = text[snippet_start:snippet_end]
                matches.append((snippet.strip(), start, end))
        return matches


def _compile_patterns() -> List[RiskPattern]:
    """Compile regex patterns for various risk categories."""
    categories: Dict[str, List[str]] = {
        "admission_of_fault": [
            r"\bwe\s+(?:are|re|were)\s+responsible\b",
            r"\bI\s+admit\b",
        ],
        "over_promise": [
            r"\bguarantee\b",
            r"\bwill\s+(?:ensure|cover|compensate)\b",
        ],
        "hostile_language": [
            r"\b(?:idiot|stupid|incompetent|useless)\b",
            r"\b(?:pay up|or else|you\s+must)\b",
        ],
        "settlement_discussion": [
            r"\b(?:settle|settlement|without prejudice)\b",
            r"\b(?:offer|demand)\s+to\s+settle\b",
        ],
        "defamation": [
            r"\b(?:fraud|scam|criminal)\b",
        ],
        "threat_of_action": [
            r"\b(?:I will sue|we'll take you to court|legal action)\b",
        ],
        "sensitive_data": [
            r"SSN\s*\d{3}-\d{2}-\d{4}",
            r"\b(?:password|credential|confidential)\b",
        ],
        "employment_discrimination": [
            r"\b(?:fired because|due to your age|because of your race)\b",
        ],
        "antitrust": [
            r"\b(?:fix prices|divide markets|collusion)\b",
        ],
    }
    patterns = []
    for category, regexes in categories.items():
        compiled = [re.compile(r, re.IGNORECASE) for r in regexes]
        patterns.append(RiskPattern(category=category, patterns=compiled))
    return patterns


# Precompile patterns once
_PATTERNS: List[RiskPattern] = _compile_patterns()


def analyze_email(email: Dict[str, str]) -> Dict[str, object]:
    """
    Analyze a single email for litigation risk.

    Parameters
    ----------
    email: Dict[str, str]
        A dictionary representing an email, expected keys:
        - 'subject' (str): the subject line
        - 'body' (str): the body content
        - other keys (ignored by this function)

    Returns
    -------
    Dict[str, object]
        A dictionary containing:
        - 'risk_score': int
        - 'risk_categories': comma‑separated string
        - 'num_flags': int
        - 'flagged_snippets': semicolon‑separated string of snippets
    """
    subject = email.get("subject", "") or ""
    body = email.get("body", "") or ""
    combined_text = f"{subject}\n{body}"

    categories_found: List[str] = []
    snippets: List[str] = []
    flag_count = 0

    for pattern in _PATTERNS:
        matches = pattern.match(combined_text)
        if matches:
            categories_found.append(pattern.category)
            flag_count += len(matches)
            for snippet, _, _ in matches:
                # Shorten snippet if extremely long
                if len(snippet) > 200:
                    snippet = snippet[:200] + "…"
                snippets.append(f"[{pattern.category}] {snippet}")

    # Simple risk score: number of categories found * number of flags
    risk_score = flag_count * (len(set(categories_found)) or 1)

    return {
        "risk_score": risk_score,
        "risk_categories": ", ".join(sorted(set(categories_found))),
        "num_flags": flag_count,
        "flagged_snippets": "; ".join(snippets),
    }


__all__ = ["analyze_email"]
