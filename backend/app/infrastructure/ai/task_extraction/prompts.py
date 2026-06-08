"""Prompt builders for task extraction.

This module is responsible for producing LLM-ready prompts that:
- instruct the model to extract actionable tasks
- extract deadlines and urgency signals
- infer task priority
- identify company names when available
- return JSON only with no additional text
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TaskExtractionPrompt:
    """Container for a task-extraction system/user prompt pair."""

    system: str
    user: str


def build_task_extraction_prompts(
    *,
    email_title: str | None,
    email_description: str | None,
    source_sender: str,
    source_company: str | None = None,
) -> TaskExtractionPrompt:
    """Build prompts for the task extraction LLM.

    Args:
        email_title: Optional title/subject context from the source email.
        email_description: Optional body/summary context from the source email.
        source_sender: Sender of the source email (used in metadata block only).
        source_company: Optional company context.

    Returns:
        A :class:`TaskExtractionPrompt` containing system and user prompt strings.
    """
    system_prompt = (
        "You are an AI assistant that extracts structured task information from emails. "
        "Follow the instructions exactly and return JSON only. "
        "Do not include markdown, preamble, or any text outside the JSON object."
    )

    user_parts: list[str] = []

    user_parts.append(
        "Task extraction instructions:\n"
        "1) Identify actionable tasks mentioned in the email.\n"
        "2) Identify any deadlines or due dates mentioned in the email.\n"
        "3) Identify urgency (signals such as 'today', 'ASAP', 'urgent', 'by EOD', etc.).\n"
        "4) Infer a task priority score based on urgency and importance. "
        "   Return priority as an integer between 0 and 100 where 0 is lowest priority and 100 is highest.\n"
        "5) Identify company names when available (use the most likely company entity).\n\n"
        "Output rules:\n"
        "- Return ONLY a single valid JSON object.\n"
        "- No explanations, no markdown, no extra text before or after the JSON.\n"
        "- Use the following JSON schema exactly:\n"
        "{\n"
        '  "tasks": [\n'
        "    {\n"
        '      "title": "<non-empty string>",\n'
        '      "description": "<string or null>",\n'
        '      "priority": <integer 0-100>,\n'
        '      "due_date": "<ISO-8601 datetime string or null>",\n'
        '      "confidence_score": <float 0.0-1.0>,\n'
        '      "source_company": "<string or null>"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "JSON field requirements:\n"
        "- tasks: array; return empty array [] if no actionable tasks are found.\n"
        "- title: non-empty string describing the task.\n"
        "- description: concise task description string, or null.\n"
        "- priority: integer in [0, 100]; use 50 as default when urgency is unclear.\n"
        "- due_date: ISO-8601 datetime string when a date is mentioned, otherwise null.\n"
        "- confidence_score: float in [0.0, 1.0] reflecting extraction confidence.\n"
        "- source_company: company name string when identifiable, otherwise null.\n"
    )

    user_parts.append("\nSource metadata:\n")
    user_parts.append(f"- source_sender: {source_sender}\n")
    user_parts.append(f"- source_company: {source_company or 'unknown'}\n")

    if email_title and email_title.strip():
        user_parts.append(f"\nEmail title:\n{email_title.strip()}\n")
    else:
        user_parts.append("\nEmail title: (none)\n")

    if email_description and email_description.strip():
        user_parts.append(f"\nEmail body/summary:\n{email_description.strip()}\n")
    else:
        user_parts.append("\nEmail body/summary: (none)\n")

    user_prompt = "".join(user_parts)

    return TaskExtractionPrompt(system=system_prompt, user=user_prompt)