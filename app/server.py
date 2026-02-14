"""FastAPI server exposing suggest/refine prompt endpoints."""

from __future__ import annotations

from typing import Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, constr

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in local environments
    def load_dotenv() -> None:
        return None

from app.git_diff_getter import EmptyDiffError, GitDiffError, InvalidRepoPathError, get_repo_diff
from app.llm.client import LLMClient, LLMClientError, MissingAPIKeyError

NonEmptyStr = constr(strip_whitespace=True, min_length=1)


class SuggestRequest(BaseModel):
    repo_path: NonEmptyStr | None = None
    diff_text: NonEmptyStr | None = None
    diff: NonEmptyStr | None = None


class RefineRequest(BaseModel):
    repo_path: NonEmptyStr | None = None
    diff_text: NonEmptyStr | None = None
    diff: NonEmptyStr | None = None
    last_prompt: NonEmptyStr | None = None
    prompt: NonEmptyStr | None = None


load_dotenv()
app = FastAPI(title="SpecPrompt API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_class=PlainTextResponse)
async def health_check() -> str:
    return "ok"


@app.post("/api/suggest", response_class=PlainTextResponse)
async def suggest(payload: SuggestRequest) -> PlainTextResponse:
    text = _run_with_error_mapping(
        lambda: _suggest_text(
            repo_path=payload.repo_path,
            diff_text=payload.diff_text,
            legacy_diff=payload.diff,
        ),
    )
    return PlainTextResponse(content=text, media_type="text/plain")


@app.post("/api/refine", response_class=PlainTextResponse)
async def refine(payload: RefineRequest) -> PlainTextResponse:
    text = _run_with_error_mapping(
        lambda: _refine_text(
            repo_path=payload.repo_path,
            diff_text=payload.diff_text,
            legacy_diff=payload.diff,
            last_prompt=payload.last_prompt,
            legacy_prompt=payload.prompt,
        ),
    )
    return PlainTextResponse(content=text, media_type="text/plain")


def _suggest_text(repo_path: str | None, diff_text: str | None, legacy_diff: str | None) -> str:
    warning, resolved_diff_text = _resolve_diff_input(
        repo_path=repo_path,
        diff_text=diff_text,
        legacy_diff=legacy_diff,
    )
    client = LLMClient()
    result = client.suggest_from_diff(resolved_diff_text)
    return _with_optional_warning(warning, result)


def _refine_text(
    repo_path: str | None,
    diff_text: str | None,
    legacy_diff: str | None,
    last_prompt: str | None,
    legacy_prompt: str | None,
) -> str:
    warning, resolved_diff_text = _resolve_diff_input(
        repo_path=repo_path,
        diff_text=diff_text,
        legacy_diff=legacy_diff,
    )
    resolved_last_prompt = _resolve_last_prompt(last_prompt=last_prompt, legacy_prompt=legacy_prompt)
    client = LLMClient()
    result = client.refine_from_diff(diff_text=resolved_diff_text, last_prompt=resolved_last_prompt)
    return _with_optional_warning(warning, result)


def _resolve_diff_input(repo_path: str | None, diff_text: str | None, legacy_diff: str | None) -> tuple[str, str]:
    manual_diff = (diff_text or legacy_diff or "").strip()
    if manual_diff:
        return "", manual_diff

    resolved_repo = (repo_path or "").strip()
    if resolved_repo:
        diff_result = get_repo_diff(repo_path=resolved_repo)
        return diff_result.warning, diff_result.diff_text

    raise ValueError("Provide either 'repo_path' or 'diff_text' in the request body.")


def _resolve_last_prompt(last_prompt: str | None, legacy_prompt: str | None) -> str:
    resolved = (last_prompt or legacy_prompt or "").strip()
    if resolved:
        return resolved
    raise ValueError("Refine mode requires 'last_prompt' (or legacy 'prompt').")


def _with_optional_warning(warning: str, body: str) -> str:
    if not warning:
        return body
    return f"{warning}\n\n{body}"


def _run_with_error_mapping(fn: Callable[[], str]) -> str:
    try:
        return fn()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidRepoPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmptyDiffError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MissingAPIKeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except GitDiffError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
