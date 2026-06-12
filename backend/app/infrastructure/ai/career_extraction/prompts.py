"""Prompt builders for the career extraction subsystem.

The functions in this module generate LLM instructions for extracting
job opportunities and interview details from email content.

No extraction logic is implemented here.
"""

from __future__ import annotations


_JOB_SYSTEM_PROMPT = (
    "You are an information extraction assistant. "
    "Your sole task is to extract job opportunity data from email content. "
    "You must return valid JSON only. "
    "Do not include markdown fences, preamble, or any text outside the JSON object."
)

_INTERVIEW_SYSTEM_PROMPT = (
    "You are an information extraction assistant. "
    "Your sole task is to extract interview scheduling data from email content. "
    "You must return valid JSON only. "
    "Do not include markdown fences, preamble, or any text outside the JSON object."
)


def build_job_opportunity_extraction_prompt(
    *,
    subject: str | None,
    body: str | None,
    extracted_links: str | None = None,
) -> tuple[str, str]:
    """Build system and user prompts for extracting job opportunities from email content.

    Args:
        subject: Email subject line (optional).
        body: Email body text (optional).
        extracted_links: Pre-extracted links from HTML body (optional).

    Returns:
        A (system_prompt, user_prompt) tuple for use with
        :meth:`~infrastructure.ai.llm.base.BaseLLMProvider.complete`.
    """
    safe_subject = subject.strip() if subject else ""
    safe_body = body.strip() if body else ""

    parts: list[str] = [
        "Extract job opportunities from the email content below.\n\n",
        "Return a JSON object matching this schema exactly:\n",
        "{\n",
        "  \"job_opportunities\": [\n",
        "    {\n",
        "      \"company\": str,\n",
        "      \"role\": str,\n",
        "      \"location\": str|null,\n",
        "      \"salary\": str|null,\n",
        "      \"apply_link\": str,\n",
        "      \"deadline\": str|null,\n",
        "      \"confidence_score\": float\n",
        "    }\n",
        "  ],\n",
        "  \"extraction_confidence\": float\n",
        "}\n\n",
        "Rules:\n",
        "- confidence_score is a float in [0.0, 1.0] per item.\n",
        "- extraction_confidence is a float in [0.0, 1.0] for the overall response.\n",
        "- If no job opportunities are found, return an empty list.\n",
        "- apply_link must be a full http/https URL. If not present, use null — "
        "but only include items where a URL can be reasonably inferred.\n",
        "- IMPORTANT: When an 'Extracted Links' section is provided below, use those "
        "URLs as the apply_link for the matching job. The links section contains the "
        "actual destination URLs decoded from tracking redirects.\n\n",
        f"Subject: {safe_subject}\n",
        f"Body:\n{safe_body}\n",
    ]

    if extracted_links:
        parts.append(f"\nExtracted Links:\n{extracted_links}\n")

    return _JOB_SYSTEM_PROMPT, "".join(parts)


def build_interview_extraction_prompt(
    *,
    subject: str | None,
    body: str | None,
    extracted_links: str | None = None,
) -> tuple[str, str]:
    """Build system and user prompts for extracting interview details from email content.

    Args:
        subject: Email subject line (optional).
        body: Email body text (optional).
        extracted_links: Pre-extracted links from HTML body (optional).

    Returns:
        A (system_prompt, user_prompt) tuple for use with
        :meth:`~infrastructure.ai.llm.base.BaseLLMProvider.complete`.
    """
    safe_subject = subject.strip() if subject else ""
    safe_body = body.strip() if body else ""

    parts: list[str] = [
        "Extract interview scheduling details from the email content below.\n\n",
        "Return a JSON object matching this schema exactly:\n",
        "{\n",
        "  \"interviews\": [\n",
        "    {\n",
        "      \"company\": str,\n",
        "      \"role\": str,\n",
        "      \"interview_date\": str|null,\n",
        "      \"meeting_link\": str,\n",
        "      \"confidence_score\": float\n",
        "    }\n",
        "  ],\n",
        "  \"extraction_confidence\": float\n",
        "}\n\n",
        "Rules:\n",
        "- confidence_score is a float in [0.0, 1.0] per item.\n",
        "- extraction_confidence is a float in [0.0, 1.0] for the overall response.\n",
        "- If no interviews are found, return an empty list.\n",
        "- meeting_link must be a full http/https URL. If not present, use null.\n",
        "- interview_date should be the raw date/time string as it appears in the email.\n",
        "- When an 'Extracted Links' section is provided, look for meeting/video call URLs.\n\n",
        f"Subject: {safe_subject}\n",
        f"Body:\n{safe_body}\n",
    ]

    if extracted_links:
        parts.append(f"\nExtracted Links:\n{extracted_links}\n")

    return _INTERVIEW_SYSTEM_PROMPT, "".join(parts)