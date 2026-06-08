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
    *, subject: str | None, body: str | None
) -> tuple[str, str]:
    """Build system and user prompts for extracting job opportunities from email content.

    Args:
        subject: Email subject line (optional).
        body: Email body text (optional).

    Returns:
        A (system_prompt, user_prompt) tuple for use with
        :meth:`~infrastructure.ai.llm.base.BaseLLMProvider.complete`.
    """
    safe_subject = subject.strip() if subject else ""
    safe_body = body.strip() if body else ""

    user_prompt = (
        "Extract job opportunities from the email content below.\n\n"
        "Return a JSON object matching this schema exactly:\n"
        "{\n"
        "  \"job_opportunities\": [\n"
        "    {\n"
        "      \"company\": str,\n"
        "      \"role\": str,\n"
        "      \"location\": str|null,\n"
        "      \"salary\": str|null,\n"
        "      \"apply_link\": str,\n"
        "      \"deadline\": str|null,\n"
        "      \"confidence_score\": float\n"
        "    }\n"
        "  ],\n"
        "  \"extraction_confidence\": float\n"
        "}\n\n"
        "Rules:\n"
        "- confidence_score is a float in [0.0, 1.0] per item.\n"
        "- extraction_confidence is a float in [0.0, 1.0] for the overall response.\n"
        "- If no job opportunities are found, return an empty list.\n"
        "- apply_link must be a full http/https URL. If not present, use null — "
        "but only include items where a URL can be reasonably inferred.\n\n"
        f"Subject: {safe_subject}\n"
        f"Body:\n{safe_body}\n"
    )

    return _JOB_SYSTEM_PROMPT, user_prompt


def build_interview_extraction_prompt(
    *, subject: str | None, body: str | None
) -> tuple[str, str]:
    """Build system and user prompts for extracting interview details from email content.

    Args:
        subject: Email subject line (optional).
        body: Email body text (optional).

    Returns:
        A (system_prompt, user_prompt) tuple for use with
        :meth:`~infrastructure.ai.llm.base.BaseLLMProvider.complete`.
    """
    safe_subject = subject.strip() if subject else ""
    safe_body = body.strip() if body else ""

    user_prompt = (
        "Extract interview scheduling details from the email content below.\n\n"
        "Return a JSON object matching this schema exactly:\n"
        "{\n"
        "  \"interviews\": [\n"
        "    {\n"
        "      \"company\": str,\n"
        "      \"role\": str,\n"
        "      \"interview_date\": str|null,\n"
        "      \"meeting_link\": str,\n"
        "      \"confidence_score\": float\n"
        "    }\n"
        "  ],\n"
        "  \"extraction_confidence\": float\n"
        "}\n\n"
        "Rules:\n"
        "- confidence_score is a float in [0.0, 1.0] per item.\n"
        "- extraction_confidence is a float in [0.0, 1.0] for the overall response.\n"
        "- If no interviews are found, return an empty list.\n"
        "- meeting_link must be a full http/https URL. If not present, use null.\n"
        "- interview_date should be the raw date/time string as it appears in the email.\n\n"
        f"Subject: {safe_subject}\n"
        f"Body:\n{safe_body}\n"
    )

    return _INTERVIEW_SYSTEM_PROMPT, user_prompt