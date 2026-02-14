
"""CLI entrypoint for suggest/refine prompt refinement workflows."""

from __future__ import annotations

import typer

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in local environments
    def load_dotenv() -> None:
        return None

from app.git_diff_getter import (
    DEFAULT_MAX_DIFF_CHARS,
    EmptyDiffError,
    GitDiffError,
    InvalidRepoPathError,
    get_repo_diff,
)
from app.llm.client import LLMClient, LLMClientError, MissingAPIKeyError

app = typer.Typer(
    name="spec-prompt",
    help="Suggest or refine the next coding prompt using git diff context.",
    add_completion=False,
)


def _run_mode(*, repo: str, max_diff_chars: int, mode: str, last_prompt: str | None = None) -> None:
    load_dotenv()
    try:
        diff_result = get_repo_diff(repo_path=repo, max_diff_chars=max_diff_chars)
        if diff_result.warning:
            typer.echo(diff_result.warning, err=True)

        client = LLMClient()

        if mode == "suggest":
            result = client.suggest_from_diff(diff_result.diff_text)
        else:
            result = client.refine_from_diff(
                diff_text=diff_result.diff_text,
                last_prompt=last_prompt or "",
            )
    except (InvalidRepoPathError, EmptyDiffError, MissingAPIKeyError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2)
    except (GitDiffError, LLMClientError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(result.rstrip())


@app.command("suggest")
def suggest(
    repo: str = typer.Option(..., "--repo", help="Path to a git repository to inspect."),
    max_diff_chars: int = typer.Option(
        DEFAULT_MAX_DIFF_CHARS,
        "--max-diff-chars",
        help=f"Maximum diff size to send to the model (default: {DEFAULT_MAX_DIFF_CHARS}).",
    ),
) -> None:
    """Generate a recommended next prompt from current git changes."""
    _run_mode(repo=repo, max_diff_chars=max_diff_chars, mode="suggest")


@app.command("refine")
def refine(
    repo: str = typer.Option(..., "--repo", help="Path to a git repository to inspect."),
    last_prompt: str = typer.Option(
        ...,
        "--last-prompt",
        help="The previous prompt to critique and rewrite.",
    ),
    max_diff_chars: int = typer.Option(
        DEFAULT_MAX_DIFF_CHARS,
        "--max-diff-chars",
        help=f"Maximum diff size to send to the model (default: {DEFAULT_MAX_DIFF_CHARS}).",
    ),
) -> None:
    """Rewrite a previous prompt using current git changes."""
    _run_mode(repo=repo, max_diff_chars=max_diff_chars, mode="refine", last_prompt=last_prompt)


if __name__ == "__main__":
    app()
