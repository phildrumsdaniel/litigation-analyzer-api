"""
FastAPI wrapper for the Email Litigation Analyzer.

This application exposes a single POST endpoint (`/analyze`) which accepts
an email’s metadata (date, sender, recipient), subject and body text.
It returns a structured JSON object containing a risk score, risk
categories, count of triggered flags, and the flagged snippets. This
enables integration with Custom GPTs via the Actions feature or with
client applications via REST calls.
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional

# Ensure the analyzer is available on the module search path. Adjust the import
# path if email_litigation_analyzer is installed elsewhere.
try:
    from email_litigation_analyzer import analyze_email
except ImportError:
    # If the analyzer isn't installed as a package, you can import it relative
    # to its location. For example:
    import sys
    from pathlib import Path
    # Add the directory containing email_litigation_analyzer.py to sys.path
    analyzer_path = Path(__file__).resolve().parent
    sys.path.append(str(analyzer_path))
    from email_litigation_analyzer import analyze_email


class EmailInput(BaseModel):
    """Schema for incoming email data."""

    date: Optional[str] = Field(
        default=None,
        description="Date the email was sent (any reasonable string format).",
        examples=["2025-01-01", "Mon, 1 Jan 2025 12:34:56 GMT"],
    )
    sender: Optional[str] = Field(
        default=None,
        description="The person or entity sending the email.",
        examples=["alice@example.com"],
    )
    to: Optional[str] = Field(
        default=None,
        description="The recipient(s) of the email.",
        examples=["bob@example.com"],
    )
    subject: str = Field(..., description="Subject line of the email.", examples=["Urgent: Settlement discussion"])
    body: str = Field(..., description="Full body of the email.", examples=["Let’s settle this matter without prejudice..."])


class AnalysisResult(BaseModel):
    """Schema for the analyzer's response."""

    risk_score: int = Field(..., description="Computed risk score; higher indicates greater litigation risk.")
    risk_categories: str = Field(
        ...,
        description="Comma-separated list of categories flagged in the email (e.g., admission_of_fault, hostile_language).",
    )
    num_flags: int = Field(..., description="Number of individual risk flags triggered.")
    flagged_snippets: str = Field(
        ...,
        description="Concise context snippets from the email that triggered the risk flags.",
    )


app = FastAPI(title="Email Litigation Analyzer API", version="1.0.0")


@app.post("/analyze", response_model=AnalysisResult)
def analyze(email: EmailInput) -> AnalysisResult:
    """Analyze an email for litigation risk and return structured results."""
    record = {
        "date": email.date or "",
        "from": email.sender or "",
        "to": email.to or "",
        "subject": email.subject,
        "body": email.body,
        "has_attachments": False,
        "source_path": "",
    }

    result = analyze_email(record)

    # Create response object; ensure keys match the Pydantic schema
    response = AnalysisResult(
        risk_score=result.get("risk_score", 0),
        risk_categories=result.get("risk_categories", ""),
        num_flags=result.get("num_flags", 0),
        flagged_snippets=result.get("flagged_snippets", ""),
    )
    return response
