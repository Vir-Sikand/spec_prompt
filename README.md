# SpecPrompt

SpecPrompt turns code changes into stronger, spec-driven prompts for AI coding workflows.

The agent logs are in ```agent_logs``` and the ***planning file*** from cursor plan mode was used to generate this quickly with 4 agents in parallel, ```agent_logs/agent_generated_plan.md```

It supports two modes:
- `suggest`: generate the next prompt from current changes
- `refine`: critique and rewrite a previous prompt using current changes

## Demo Link

Hosted app:
- `https://spec-prompt.vercel.app`

Use this when you just want to open the app and run it in-browser with pasted diff input.

## Inputs Supported

The backend supports both input styles:

1) Repo path input (best for local backend on your own machine)
- `repo_path` points to a local git repository

2) Pasted diff input (best for hosted/demo use)
- `diff_text` contains the git diff text directly

For `refine`, include:
- `last_prompt` (or legacy `prompt`)

## Full Local Setup (Backend + UI + CLI)

### 1) Create environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure environment variables

```bash
cp .env.example .env
```

Set in `.env`:

```env
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini
```

`OPENAI_MODEL` is optional.

### 3) Run backend locally

```bash
uvicorn app.server:app --reload --port 8000
```

### 4) Run static UI locally

```bash
python -m http.server 5500 --directory static
```

Open:
- `http://127.0.0.1:5500`

In the UI:
- leave `API Base URL` blank (auto-resolves to `http://127.0.0.1:8000` when served on `:5500`)
- choose `Use Repo Path` to analyze local repositories
- choose `Paste Git Diff` to send raw diff text

## Local CLI Usage (Repo Path Workflow)

Run from this project root:

```bash
python -m app.main suggest --repo /absolute/path/to/target/repo
```

```bash
python -m app.main refine \
  --repo /absolute/path/to/target/repo \
  --last-prompt "Rewrite the auth endpoint with better validation"
```

### Local CLI examples with your own machine path

```bash
python -m app.main suggest --repo /Users/yourname/Projects/your-repo
```

```bash
python -m app.main refine \
  --repo /Users/yourname/Projects/your-repo \
  --last-prompt "Implement caching around database reads"
```

## Hosted App Workflow (For Users With Demo Link)

If a user only has the demo link and no local backend:
1. Open `https://spec-prompt.vercel.app`
2. Select `Paste Git Diff`
3. Paste a diff
4. Run `Suggest` or `Refine` (include last prompt for refine)

### Fast way to copy staged diff (macOS)

```bash
git diff --cached | pbcopy
```

Then paste into the app.

### Sample diff to test immediately

```diff
diff --git a/api/index.py b/api/index.py
new file mode 100644
index 0000000..df4ba1e
--- /dev/null
+++ b/api/index.py
@@ -0,0 +1,114 @@
+"""Vercel serverless entrypoint - FastAPI application for SpecPrompt."""
+
+from __future__ import annotations
+
+import os
+import sys
+from pathlib import Path
+
+from fastapi import FastAPI, HTTPException
+from fastapi.middleware.cors import CORSMiddleware
+from fastapi.responses import FileResponse, JSONResponse
+from pydantic import BaseModel, Field
+
+# ---------------------------------------------------------------------------
+# Ensure the project root is on sys.path so `app.*` imports resolve when
+# running inside Vercel's serverless environment.
+# ---------------------------------------------------------------------------
+_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
+if _PROJECT_ROOT not in sys.path:
+    sys.path.insert(0, _PROJECT_ROOT)
+
+from app.llm import build_suggest_prompt, build_refine_prompt, call_llm  # noqa: E402
+
+# ---------------------------------------------------------------------------
+# FastAPI app
+# ---------------------------------------------------------------------------
+app = FastAPI(
+    title="SpecPrompt API",
+    description="Spec-driven prompt suggestion & refinement for Cursor users.",
+    version="0.1.0",
+)
+
+# CORS - allow the static frontend (and local dev) to reach the API.
+app.add_middleware(
+    CORSMiddleware,
+    allow_origins=["*"],
+    allow_credentials=True,
+    allow_methods=["*"],
+    allow_headers=["*"],
+)
+
+# ---------------------------------------------------------------------------
+# Request / response models
+# ---------------------------------------------------------------------------
+
+
+class SuggestRequest(BaseModel):
+    diff: str = Field(..., min_length=1, description="Git diff text to analyze.")
+
+
+class RefineRequest(BaseModel):
+    diff: str = Field(..., min_length=1, description="Git diff text to analyze.")
+    prompt: str = Field(..., min_length=1, description="The original user prompt to critique and rewrite.")
+
+
+class SuggestResponse(BaseModel):
+    suggestion: str
+
+
+class RefineResponse(BaseModel):
+    result: str
+
+
+# ---------------------------------------------------------------------------
+# API endpoints
+# ---------------------------------------------------------------------------
+
+
+@app.post("/api/suggest", response_model=SuggestResponse)
+async def suggest(body: SuggestRequest) -> SuggestResponse:
+    """Suggest mode: given a git diff, return a spec-driven next prompt."""
+    try:
+        messages = build_suggest_prompt(body.diff)
+        result = call_llm(messages)
+        return SuggestResponse(suggestion=result)
+    except Exception as exc:
+        raise HTTPException(status_code=500, detail=str(exc)) from exc
+
+
+@app.post("/api/refine", response_model=RefineResponse)
+async def refine(body: RefineRequest) -> RefineResponse:
+    """Refine mode: critique the original prompt and return a rewritten version."""
+    try:
+        messages = build_refine_prompt(body.diff, body.prompt)
+        result = call_llm(messages)
+        return RefineResponse(result=result)
+    except Exception as exc:
+        raise HTTPException(status_code=500, detail=str(exc)) from exc
+
+
+# ---------------------------------------------------------------------------
+# Health-check
+# ---------------------------------------------------------------------------
+
+
+@app.get("/api/health")
+async def health() -> JSONResponse:
+    return JSONResponse({"status": "ok"})
+
+
+# ---------------------------------------------------------------------------
+# Serve the static frontend at the root path.
+# In production Vercel routing handles this via vercel.json, but this
+# fallback is useful for local development with `uvicorn api.index:app`.
+# ---------------------------------------------------------------------------
+_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
+
+
+@app.get("/")
+async def serve_index() -> FileResponse:
+    index_path = _STATIC_DIR / "index.html"
+    if not index_path.exists():
+        raise HTTPException(status_code=404, detail="Frontend not built yet.")
+    return FileResponse(str(index_path), media_type="text/html")
```

## API Request Examples

### Suggest with repo path

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/suggest" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/absolute/path/to/repo"
  }'
```

### Suggest with pasted diff

```bash
curl -sS -X POST "https://spec-prompt.vercel.app/api/suggest" \
  -H "Content-Type: application/json" \
  -d '{
    "diff_text": "diff --git a/file.py b/file.py\n..."
  }'
```

### Refine with repo path

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/refine" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/absolute/path/to/repo",
    "last_prompt": "Add retries around upstream API calls"
  }'
```

### Refine with pasted diff

```bash
curl -sS -X POST "https://spec-prompt.vercel.app/api/refine" \
  -H "Content-Type: application/json" \
  -d '{
    "diff_text": "diff --git a/file.py b/file.py\n...",
    "last_prompt": "Build a robust background worker for this service"
  }'
```

## Local Prompt Text You Can Reuse

Use any of these in refine mode (`last_prompt`):

- `Implement JWT authentication for the API.`
- `Add pagination and filtering to the users endpoint.`
- `Refactor the DB layer to use transactions for writes.`
- `Add tests for edge cases around empty and malformed input.`

## Notes

- On hosted Vercel, local machine paths (like `/Users/...`) are not accessible.
- For hosted usage, use pasted diff input.
- For local usage with your own repository path, run the backend on your machine and use repo path mode.
