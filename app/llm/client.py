"""OpenAI client for suggest/refine prompt refinement flows."""

from __future__ import annotations

from dataclasses import dataclass
import os

from openai import OpenAI

from app.llm.prompt_builder import (
    build_refine_prompt,
    build_suggest_prompt,
    normalize_refine_output,
    normalize_suggest_output,
)


DEFAULT_MODEL = "gpt-4o-mini"


class LLMClientError(RuntimeError):
    """Raised when the LLM client cannot complete a request."""


class MissingAPIKeyError(LLMClientError):
    """Raised when OPENAI_API_KEY is missing."""


@dataclass(frozen=True)
class LLMConfig:
    model: str = DEFAULT_MODEL
    temperature: float = 0.2
    max_tokens: int = 1200
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "LLMConfig":
        model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        return cls(model=model)


class LLMClient:
    """Small wrapper around OpenAI chat completions for this app."""

    def __init__(self, api_key: str | None = None, config: LLMConfig | None = None) -> None:
        resolved_key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
        if not resolved_key:
            raise MissingAPIKeyError("Missing OPENAI_API_KEY in environment.")

        self.config = config or LLMConfig.from_env()
        self._client = OpenAI(api_key=resolved_key, timeout=self.config.timeout_seconds)

    def suggest_from_diff(self, diff_text: str) -> str:
        package = build_suggest_prompt(diff_text)
        model_output = self._complete(
            system_prompt=package.system_prompt,
            user_prompt=package.user_prompt,
        )
        normalized = normalize_suggest_output(model_output)
        return _prepend_truncation_warning(normalized, package.truncation_note)

    def refine_from_diff(self, diff_text: str, last_prompt: str) -> str:
        if not last_prompt or not last_prompt.strip():
            raise LLMClientError("Refine mode requires a non-empty last prompt.")

        package = build_refine_prompt(diff_text=diff_text, last_prompt=last_prompt)
        model_output = self._complete(
            system_prompt=package.system_prompt,
            user_prompt=package.user_prompt,
        )
        normalized = normalize_refine_output(model_output)
        return _prepend_truncation_warning(normalized, package.truncation_note)

    def _complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:  # pragma: no cover - external SDK behavior
            raise LLMClientError(f"OpenAI request failed: {exc}") from exc

        if not response.choices:
            raise LLMClientError("OpenAI returned no completion choices.")

        text = response.choices[0].message.content or ""
        if not text.strip():
            raise LLMClientError("OpenAI returned an empty completion.")
        return text.strip()


def _prepend_truncation_warning(output_text: str, truncation_note: str) -> str:
    if not truncation_note:
        return output_text
    return f"{truncation_note}\n\n{output_text}"
