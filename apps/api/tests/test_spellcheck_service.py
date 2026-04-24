"""Unit tests for Romanian spell-check service behavior."""

from __future__ import annotations

from types import SimpleNamespace

from app.services import spellcheck_service


def test_spellcheck_returns_unavailable_when_tool_missing(monkeypatch) -> None:
    monkeypatch.setattr(spellcheck_service, "_get_tool", lambda _lang: (None, "not installed"))
    result = spellcheck_service.spellcheck_text_ro("Acesta estee text.")

    assert result.available is False
    assert result.issues == []
    assert any("not installed" in warning for warning in result.warnings)


def test_spellcheck_extracts_issues_and_duplicates(monkeypatch) -> None:
    text = "Acesta estee un texxt. estee"

    fake_matches = [
        SimpleNamespace(
            offset=7,
            errorLength=5,
            message="Possible spelling mistake found.",
            replacements=["este"],
            ruleId="MORFOLOGIK_RULE_RO_RO",
            ruleIssueType="misspelling",
            category=SimpleNamespace(id="TYPOS"),
        ),
        SimpleNamespace(
            offset=16,
            errorLength=5,
            message="Possible spelling mistake found.",
            replacements=["text"],
            ruleId="MORFOLOGIK_RULE_RO_RO",
            ruleIssueType="misspelling",
            category=SimpleNamespace(id="TYPOS"),
        ),
        SimpleNamespace(
            offset=23,
            errorLength=5,
            message="Possible spelling mistake found.",
            replacements=["este"],
            ruleId="MORFOLOGIK_RULE_RO_RO",
            ruleIssueType="misspelling",
            category=SimpleNamespace(id="TYPOS"),
        ),
    ]
    fake_tool = SimpleNamespace(check=lambda _t: fake_matches)
    monkeypatch.setattr(spellcheck_service, "_get_tool", lambda _lang: (fake_tool, None))

    result = spellcheck_service.spellcheck_text_ro(text, include_corrected_text=True)

    assert result.available is True
    assert len(result.issues) == 3
    assert result.duplicate_tokens[0]["token"] == "estee"
    assert result.duplicate_tokens[0]["count"] == 2
    assert result.corrected_text is not None
    assert "este" in result.corrected_text


def test_spellcheck_safe_mode_auto_apply(monkeypatch) -> None:
    text = "estee"
    fake_matches = [
        SimpleNamespace(
            offset=0,
            errorLength=5,
            message="Possible spelling mistake found.",
            replacements=["este"],
            ruleId="MORFOLOGIK_RULE_RO_RO",
            ruleIssueType="misspelling",
            category=SimpleNamespace(id="TYPOS"),
        )
    ]
    fake_tool = SimpleNamespace(check=lambda _t: fake_matches)
    monkeypatch.setattr(spellcheck_service, "_get_tool", lambda _lang: (fake_tool, None))

    result = spellcheck_service.spellcheck_text_ro(
        text,
        include_corrected_text=True,
        auto_apply_mode="safe",
        min_confidence=0.5,
    )

    assert result.issues[0].auto_applied is True
    assert result.issues[0].chosen_replacement == "este"
    assert result.corrected_text == "este"
