import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

_PROFANITY_PATTERNS = [
    re.compile(r"\b(damn|hell|crap)\b", re.IGNORECASE),
]


class GuardrailViolation(Exception):
    def __init__(self, rule: str, message: str):
        self.rule = rule
        super().__init__(message)


def apply_input_guardrails(text: str, config: dict[str, Any]) -> str:
    if config.get("block_profanity"):
        for pat in _PROFANITY_PATTERNS:
            if pat.search(text):
                raise GuardrailViolation("block_profanity", "Input contains blocked language")

    allowed_topics = config.get("allowed_topics")
    if allowed_topics:
        logger.debug("Topic guardrail active: %s", allowed_topics)

    max_input_tokens = config.get("max_input_tokens")
    if max_input_tokens:
        word_count = len(text.split())
        if word_count > max_input_tokens:
            text = " ".join(text.split()[:max_input_tokens])
            logger.warning("Input truncated to %d tokens", max_input_tokens)

    return text


def apply_output_guardrails(text: str, config: dict[str, Any]) -> str:
    if config.get("block_pii"):
        email_pat = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
        phone_pat = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
        if email_pat.search(text) or phone_pat.search(text):
            raise GuardrailViolation("block_pii", "Output contains potential PII")

    max_output_length = config.get("max_output_length")
    if max_output_length and len(text) > max_output_length:
        text = text[:max_output_length] + "..."
        logger.warning("Output truncated to %d chars", max_output_length)

    required_format = config.get("required_format")
    if required_format == "json":
        import json
        try:
            json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Output failed JSON format guardrail")

    return text
