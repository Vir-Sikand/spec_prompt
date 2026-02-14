"""Utilities for reading staged + unstaged git diffs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


DEFAULT_MAX_DIFF_CHARS = 120_000


class GitDiffError(RuntimeError):
    """Base class for git diff retrieval errors."""


class InvalidRepoPathError(GitDiffError):
    """Raised when the given repo path is missing or not a git repo."""


class EmptyDiffError(GitDiffError):
    """Raised when no staged/unstaged changes are present."""


@dataclass(frozen=True)
class DiffResult:
    """Normalized git diff payload consumed by CLI and API layers."""

    diff_text: str
    was_truncated: bool
    warning: str


def get_repo_diff(repo_path: str, max_diff_chars: int = DEFAULT_MAX_DIFF_CHARS) -> DiffResult:
    """Return staged + unstaged diff text from the given git repository path."""
    repo = _validate_repo_path(repo_path)

    unstaged = _run_git(repo, ["diff"])
    staged = _run_git(repo, ["diff", "--cached"])

    sections: list[str] = []
    if unstaged.strip():
        sections.append("### UNSTAGED CHANGES\n" + unstaged.strip())
    if staged.strip():
        sections.append("### STAGED CHANGES\n" + staged.strip())

    if not sections:
        raise EmptyDiffError("No staged or unstaged changes found in the repository.")

    full_diff = "\n\n".join(sections).strip()
    if len(full_diff) <= max_diff_chars:
        return DiffResult(diff_text=full_diff, was_truncated=False, warning="")

    truncated = full_diff[:max_diff_chars].rstrip()
    warning = (
        f"Warning: git diff exceeded {max_diff_chars} characters and was truncated "
        "before sending to the model."
    )
    return DiffResult(diff_text=truncated, was_truncated=True, warning=warning)


def _validate_repo_path(repo_path: str) -> Path:
    path = Path(repo_path).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise InvalidRepoPathError(f"Invalid repo path: '{repo_path}' does not exist.")

    try:
        check = _run_git(path, ["rev-parse", "--is-inside-work-tree"])
    except GitDiffError as exc:
        raise InvalidRepoPathError(f"Path is not a git repository: '{repo_path}'.") from exc

    if check.strip().lower() != "true":
        raise InvalidRepoPathError(f"Path is not a git repository: '{repo_path}'.")
    return path


def _run_git(repo_path: Path, args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        message = stderr or "Unknown git command failure."
        raise GitDiffError(f"Git command failed ({' '.join(args)}): {message}") from exc

    return completed.stdout
