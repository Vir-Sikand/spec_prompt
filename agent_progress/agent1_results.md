# Agent 1 Progress - Core LLM

## Status
Completed.

## Scope Implemented
- Implemented `app/llm/prompt_builder.py`.
- Implemented `app/llm/client.py`.
- Added package markers: `app/__init__.py` and `app/llm/__init__.py`.

## What Was Built
### 1) Prompt templates (suggest + refine)
- Added `build_suggest_prompt(...)` and `build_refine_prompt(...)`.
- Each template enforces spec-driven output expectations:
  - objective/scope clarity
  - architecture constraints and interfaces
  - edge cases/failure modes
  - test strategy and acceptance criteria
  - ordered implementation steps

### 2) Diff truncation handling
- Added bounded diff handling with `DEFAULT_MAX_DIFF_CHARS`.
- Prompts include a truncation warning when the diff is cut.

### 3) Deterministic plain-text section ordering
- Added normalization helpers:
  - `normalize_suggest_output(...)`
  - `normalize_refine_output(...)`
- These normalize responses into stable heading order and fill missing sections with `Not provided.`

### 4) OpenAI client wrapper
- Added `LLMClient` with:
  - env-backed API key (`OPENAI_API_KEY`)
  - default model fallback (`OPENAI_MODEL` or `gpt-4o-mini`)
  - explicit error types (`LLMClientError`, `MissingAPIKeyError`)
  - mode methods:
    - `suggest_from_diff(...)`
    - `refine_from_diff(...)`
- Responses are post-processed through the normalization layer before returning.

## Validation
- Python compile check passed for Agent 1 files.
- Cursor lint diagnostics reported no issues.
