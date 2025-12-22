"""JSON utility functions for parsing LLM responses."""


def strip_markdown_json(text: str) -> str:
    """Strip markdown code blocks from JSON response.

    LLMs often wrap JSON responses in markdown code blocks (```json ... ```).
    This function removes those wrappers to extract clean JSON.

    Args:
        text: Raw text that may contain markdown-wrapped JSON.

    Returns:
        Clean JSON string with markdown wrappers removed.

    Example:
        >>> strip_markdown_json("```json\\n{\"key\": \"value\"}\\n```")
        '{"key": "value"}'
    """
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
