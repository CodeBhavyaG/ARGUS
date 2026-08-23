"""Configuration for the Research Brief Agent."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


class ResearchBriefConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    llm_provider: str = Field(default_factory=lambda: _env("LLM_PROVIDER", "groq" if _env("GROQ_API_KEY") else "openai") or "openai")
    llm_model: str = Field(default_factory=lambda: _env("LLM_MODEL", "openai/gpt-oss-120b") or "openai/gpt-oss-120b")
    llm_api_key: str | None = Field(default_factory=lambda: _env("RESEARCH_BRIEF_LLM_API_KEY") or _env("GROQ_API_KEY") or _env("OPENAI_API_KEY") or _env("ANTHROPIC_API_KEY") or _env("API_KEY"))
    max_completion_tokens: int = Field(default_factory=lambda: int(_env("RESEARCH_BRIEF_MAX_COMPLETION_TOKENS", "4096") or "4096"), ge=1)
    top_p: float = Field(default_factory=lambda: float(_env("GROQ_TOP_P", "1") or "1"), gt=0, le=1)
    reasoning_effort: str = Field(default_factory=lambda: _env("GROQ_REASONING_EFFORT", "medium") or "medium")
    temperature: float = Field(default=0.2, ge=0, le=2)
