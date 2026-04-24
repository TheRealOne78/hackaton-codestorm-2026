"""Romanian spell-check service based on `language_tool_python`."""

from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

try:
    import language_tool_python
except Exception:  # pragma: no cover - import failures are handled in runtime output
    language_tool_python = None  # type: ignore[assignment]

from app.schemas.blockers import SpellIssue, SpellcheckResult

WORD_RE = re.compile(r"^[A-Za-zĂÂÎȘȚăâîșț\-]+$")
CAPITALIZED_WORD_RE = re.compile(r"^[A-ZĂÂÎȘȚ][a-zăâîșț]+$")

_TOOL_CACHE: dict[str, Any] = {}


def _get_tool(language: str) -> tuple[Any | None, str | None]:
    """Return a cached LanguageTool instance for the requested language."""
    if language_tool_python is None:
        return None, "language_tool_python is not installed"

    if language in _TOOL_CACHE:
        return _TOOL_CACHE[language], None

    try:
        tool = language_tool_python.LanguageTool(language)
    except Exception as exc:  # pragma: no cover - dependent on local Java/LT runtime
        return None, f"LanguageTool init failed: {exc}"

    _TOOL_CACHE[language] = tool
    return tool, None


def _is_spell_like_issue(text: str, match: Any) -> bool:
    """Heuristically keep spelling-like issues and drop grammar/style findings."""
    offset = int(getattr(match, "offset", 0))
    length = int(getattr(match, "errorLength", getattr(match, "error_length", 0)))
    token = text[offset : offset + length].strip()
    if not token or " " in token:
        return False
    if not WORD_RE.fullmatch(token):
        return False

    issue_type = str(getattr(match, "ruleIssueType", getattr(match, "rule_issue_type", ""))).lower()
    rule_id = str(getattr(match, "ruleId", getattr(match, "rule_id", ""))).upper()
    if issue_type in {"misspelling", "typographical"}:
        return True
    if "MORFOLOGIK" in rule_id:
        return True

    # Fallback: if we have a word token + suggestions, treat it as spelling.
    replacements = list(getattr(match, "replacements", []) or [])
    return len(replacements) > 0


def _apply_replacements(text: str, issues: list[SpellIssue]) -> str:
    """Apply chosen replacements from right to left for stable offsets."""
    corrected = text
    ordered = sorted(issues, key=lambda item: item.offset, reverse=True)
    for issue in ordered:
        replacement = issue.chosen_replacement or (issue.replacements[0] if issue.replacements else None)
        if not replacement:
            continue
        start = issue.offset
        end = start + issue.length
        corrected = corrected[:start] + replacement + corrected[end:]
    return corrected


def _candidate_confidence(token: str, suggestion: str) -> float:
    """Compute confidence score for replacing token with suggestion."""
    token_n = token.lower().strip()
    suggestion_n = suggestion.lower().strip()
    if not token_n or not suggestion_n:
        return 0.0
    base = SequenceMatcher(None, token_n, suggestion_n).ratio()
    length_gap = abs(len(token_n) - len(suggestion_n))
    penalty = min(0.18, length_gap * 0.03)
    return max(0.0, min(1.0, base - penalty))


def _should_auto_apply(
    token: str,
    suggestion: str,
    confidence: float,
    mode: str,
    min_confidence: float,
) -> bool:
    """Decide whether a suggestion should be auto-applied."""
    if mode == "off":
        return False
    if confidence < min_confidence:
        return False
    if mode == "safe":
        if CAPITALIZED_WORD_RE.match(token):
            return False
        if abs(len(token) - len(suggestion)) > 2:
            return False
    return True


def spellcheck_text_ro(
    text: str,
    language: str = "ro-RO",
    max_issues: int = 200,
    include_corrected_text: bool = False,
    auto_apply_mode: str = "off",
    min_confidence: float = 0.84,
    custom_dictionary: list[str] | None = None,
) -> SpellcheckResult:
    """Run Romanian spell-check and return deterministic structured issues."""
    dict_words = {w.strip().lower() for w in (custom_dictionary or []) if w.strip()}
    tool, init_error = _get_tool(language)
    if init_error:
        return SpellcheckResult(
            available=False,
            language=language,
            issues=[],
            duplicate_tokens=[],
            corrected_text=None,
            auto_apply_mode="off",
            warnings=[init_error],
        )

    try:
        matches = tool.check(text)
    except Exception as exc:  # pragma: no cover - depends on LT runtime/server behavior
        return SpellcheckResult(
            available=False,
            language=language,
            issues=[],
            duplicate_tokens=[],
            corrected_text=None,
            auto_apply_mode="off",
            warnings=[f"LanguageTool check failed: {exc}"],
        )

    issues: list[SpellIssue] = []
    for match in matches:
        if len(issues) >= max_issues:
            break
        if not _is_spell_like_issue(text, match):
            continue

        offset = int(getattr(match, "offset", 0))
        length = int(getattr(match, "errorLength", getattr(match, "error_length", 0)))
        token = text[offset : offset + length].strip()
        if token.lower() in dict_words:
            continue
        replacements = [str(rep) for rep in list(getattr(match, "replacements", []) or [])][:6]
        category = getattr(match, "category", None)
        category_id = str(getattr(category, "id", category)) if category is not None else None
        best = replacements[0] if replacements else None
        confidence = _candidate_confidence(token, best) if best else 0.0
        auto_applied = bool(best) and _should_auto_apply(token, best, confidence, auto_apply_mode, min_confidence)

        issues.append(
            SpellIssue(
                token=token,
                offset=offset,
                length=length,
                message=str(getattr(match, "message", "Possible spelling issue")),
                replacements=replacements,
                rule_id=str(getattr(match, "ruleId", getattr(match, "rule_id", "UNKNOWN"))),
                category=category_id,
                confidence=round(confidence, 3),
                chosen_replacement=best if auto_applied else None,
                auto_applied=auto_applied,
            )
        )

    token_counter = Counter(issue.token.lower() for issue in issues if issue.token)
    duplicate_tokens = sorted(
        [{"token": token, "count": count} for token, count in token_counter.items() if count > 1],
        key=lambda item: (-int(item["count"]), str(item["token"])),
    )

    corrected_text = _apply_replacements(text, issues) if include_corrected_text else None

    return SpellcheckResult(
        available=True,
        language=language,
        issues=issues,
        duplicate_tokens=duplicate_tokens,
        corrected_text=corrected_text,
        auto_apply_mode=auto_apply_mode if auto_apply_mode in {"off", "safe", "aggressive"} else "off",
        warnings=[],
    )


def spellcheck_parsed_payload_ro(parsed: dict[str, Any], custom_dictionary: list[str] | None = None) -> dict[str, Any]:
    """Run field-level spell-check over parsed payload text fields."""
    result: dict[str, Any] = {}
    text_fields = ["title", "objectives"]
    for field in text_fields:
        value = parsed.get(field)
        if isinstance(value, str) and value.strip():
            checked = spellcheck_text_ro(value, include_corrected_text=False, custom_dictionary=custom_dictionary)
            result[field] = checked.model_dump()

    bibliography = parsed.get("bibliography")
    if isinstance(bibliography, list):
        items: list[dict[str, Any]] = []
        for idx, entry in enumerate(bibliography):
            if isinstance(entry, str) and entry.strip():
                checked = spellcheck_text_ro(entry, include_corrected_text=False, custom_dictionary=custom_dictionary)
                items.append({"index": idx, "value": entry, "spellcheck": checked.model_dump()})
        if items:
            result["bibliography"] = items
    return result
