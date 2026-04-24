"""Romanian spell-check service based on `language_tool_python`."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

try:
    import language_tool_python
except Exception:  # pragma: no cover - import failures are handled in runtime output
    language_tool_python = None  # type: ignore[assignment]

from app.schemas.blockers import SpellIssue, SpellcheckResult

WORD_RE = re.compile(r"^[A-Za-zĂÂÎȘȚăâîșț\-]+$")

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
    """Apply first suggestion for each issue from right to left for stable offsets."""
    corrected = text
    ordered = sorted(issues, key=lambda item: item.offset, reverse=True)
    for issue in ordered:
        if not issue.replacements:
            continue
        start = issue.offset
        end = start + issue.length
        corrected = corrected[:start] + issue.replacements[0] + corrected[end:]
    return corrected


def spellcheck_text_ro(
    text: str,
    language: str = "ro-RO",
    max_issues: int = 200,
    include_corrected_text: bool = True,
) -> SpellcheckResult:
    """Run Romanian spell-check and return deterministic structured issues."""
    tool, init_error = _get_tool(language)
    if init_error:
        return SpellcheckResult(
            available=False,
            language=language,
            issues=[],
            duplicate_tokens=[],
            corrected_text=None,
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
        replacements = [str(rep) for rep in list(getattr(match, "replacements", []) or [])][:6]
        category = getattr(match, "category", None)
        category_id = str(getattr(category, "id", category)) if category is not None else None

        issues.append(
            SpellIssue(
                token=token,
                offset=offset,
                length=length,
                message=str(getattr(match, "message", "Possible spelling issue")),
                replacements=replacements,
                rule_id=str(getattr(match, "ruleId", getattr(match, "rule_id", "UNKNOWN"))),
                category=category_id,
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
        warnings=[],
    )

