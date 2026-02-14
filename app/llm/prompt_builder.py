"""Prompt templates and output normalization for suggest/refine modes."""

from __future__ import annotations

from dataclasses import dataclass
import re


DEFAULT_MAX_DIFF_CHARS = 24_000

SUGGEST_SECTION_ORDER = [
    "Project Understanding",
    "Recommended Next Prompt",
    "Alternate Prompt Options",
    "Edge-Case Checklist",
]

REFINE_SECTION_ORDER = [
    "Why Previous Prompt Is Underspecified",
    "Rewritten Spec-Driven Prompt",
    "Assumptions To Confirm",
    "Edge-Case Checklist",
]


@dataclass(frozen=True)
class PromptPackage:
    system_prompt: str
    user_prompt: str
    was_diff_truncated: bool
    truncation_note: str


def build_suggest_prompt(diff_text: str, max_diff_chars: int = DEFAULT_MAX_DIFF_CHARS) -> PromptPackage:
    """Build the mode-specific prompt package for suggest mode."""
    bounded_diff, was_truncated = _truncate_diff(diff_text, max_diff_chars=max_diff_chars)
    truncation_note = (
        f"Warning: git diff exceeded {max_diff_chars} characters and was truncated."
        if was_truncated
        else ""
    )

    system_prompt = (
        "You are a senior staff engineer helping developers craft the next high-quality coding prompt. "
        "Always produce plain text with these exact sections and in this exact order:\n"
        "1) Project Understanding\n"
        "2) Recommended Next Prompt\n"
        "3) Alternate Prompt Options\n"
        "4) Edge-Case Checklist\n\n"
        "Be concrete and implementation-oriented. Prioritize architecture clarity, edge cases, testability, "
        "and acceptance criteria. Do not return JSON."
    )

    user_prompt = (
        "Task mode: SUGGEST.\n"
        "Given this git diff, propose the best next prompt to continue implementation.\n"
        "The prompt should specify objective, scope boundaries, interfaces/constraints, edge cases, "
        "tests, and ordered implementation steps.\n\n"
        f"{truncation_note}\n\n"
        "Git diff:\n"
        "```diff\n"
        f"{bounded_diff}\n"
        "```"
    )

    return PromptPackage(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        was_diff_truncated=was_truncated,
        truncation_note=truncation_note,
    )


def build_refine_prompt(
    diff_text: str,
    last_prompt: str,
    max_diff_chars: int = DEFAULT_MAX_DIFF_CHARS,
) -> PromptPackage:
    """Build the mode-specific prompt package for refine mode."""
    bounded_diff, was_truncated = _truncate_diff(diff_text, max_diff_chars=max_diff_chars)
    truncation_note = (
        f"Warning: git diff exceeded {max_diff_chars} characters and was truncated."
        if was_truncated
        else ""
    )

    system_prompt = (
        "You are a principal engineer and prompt quality reviewer. "
        "Always produce plain text with these exact sections and in this exact order:\n"
        "1) Why Previous Prompt Is Underspecified\n"
        "2) Rewritten Spec-Driven Prompt\n"
        "3) Assumptions To Confirm\n"
        "4) Edge-Case Checklist\n\n"
        "Focus on missing requirements, architecture constraints, failure modes, acceptance criteria, "
        "and test strategy. Do not return JSON."
    )

    user_prompt = (
        "Task mode: REFINE.\n"
        "Analyze the previous prompt and improve it using the current git diff context.\n"
        "The rewritten prompt must be explicit about objective, scope, constraints/interfaces, edge cases, "
        "test/validation plan, and ordered implementation steps.\n\n"
        f"{truncation_note}\n\n"
        "Previous prompt:\n"
        "<<<LAST_PROMPT\n"
        f"{last_prompt}\n"
        "LAST_PROMPT>>>\n\n"
        "Git diff:\n"
        "```diff\n"
        f"{bounded_diff}\n"
        "```"
    )

    return PromptPackage(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        was_diff_truncated=was_truncated,
        truncation_note=truncation_note,
    )


def normalize_suggest_output(raw_text: str) -> str:
    """Normalize suggest output to deterministic section order."""
    alias_map = {
        "Project Understanding": ("project understanding", "context summary", "understanding"),
        "Recommended Next Prompt": ("recommended next prompt", "next prompt", "primary prompt"),
        "Alternate Prompt Options": ("alternate prompt options", "alternates", "alternative prompts"),
        "Edge-Case Checklist": ("edge-case checklist", "edge cases", "failure modes"),
    }
    return _normalize_sections(raw_text, SUGGEST_SECTION_ORDER, alias_map)


def normalize_refine_output(raw_text: str) -> str:
    """Normalize refine output to deterministic section order."""
    alias_map = {
        "Why Previous Prompt Is Underspecified": (
            "why previous prompt is underspecified",
            "underspecification",
            "gaps",
        ),
        "Rewritten Spec-Driven Prompt": (
            "rewritten spec-driven prompt",
            "rewritten prompt",
            "improved prompt",
        ),
        "Assumptions To Confirm": ("assumptions to confirm", "assumptions", "open questions"),
        "Edge-Case Checklist": ("edge-case checklist", "edge cases", "failure modes"),
    }
    return _normalize_sections(raw_text, REFINE_SECTION_ORDER, alias_map)


def _truncate_diff(diff_text: str, max_diff_chars: int) -> tuple[str, bool]:
    clean = diff_text.strip()
    if len(clean) <= max_diff_chars:
        return clean, False
    return clean[:max_diff_chars], True


def _normalize_sections(raw_text: str, ordered_sections: list[str], alias_map: dict[str, tuple[str, ...]]) -> str:
    lines = [line.rstrip() for line in raw_text.splitlines()]
    sections: dict[str, list[str]] = {name: [] for name in ordered_sections}
    current = ordered_sections[0]

    for line in lines:
        candidate = _match_canonical_heading(line, ordered_sections, alias_map)
        if candidate:
            current = candidate
            continue
        sections[current].append(line)

    rendered = []
    for section_name in ordered_sections:
        content = "\n".join(sections[section_name]).strip()
        if not content:
            content = "Not provided."
        rendered.append(f"## {section_name}\n{content}")
    return "\n\n".join(rendered).strip() + "\n"


def _match_canonical_heading(
    line: str,
    ordered_sections: list[str],
    alias_map: dict[str, tuple[str, ...]],
) -> str | None:
    """Try to match a heading-like line to a canonical section name."""
    stripped = line.strip().lower()
    stripped = re.sub(r"^#{1,6}\s*", "", stripped)
    stripped = re.sub(r"^\d+[\)\.\-:\s]+", "", stripped)
    stripped = stripped.strip(" :-")

    for canonical in ordered_sections:
        aliases = alias_map.get(canonical, ())
        candidates = (canonical.lower(), *aliases)
        for alias in candidates:
            if stripped == alias:
                return canonical
    return None
