"""Pydantic schemas and configuration models for the Research Agent layer."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SearchResultItem(BaseModel):
    """A single retrieved search result item with metadata and citations."""
    title: str = ""
    url: str = ""
    snippet: str = ""
    score: Optional[float] = None
    domain: Optional[str] = None


class SearchQuery(BaseModel):
    """A structured search query generated during task decomposition."""
    query: str
    rationale: Optional[str] = None


class QueryPlan(BaseModel):
    """Plan containing expanded queries to investigate a research task."""
    queries: List[SearchQuery] = Field(default_factory=list)


class ResearchEvidence(BaseModel):
    """Aggregated evidence retrieved from web search queries."""
    task_id: str
    task_description: str
    queries: List[str] = Field(default_factory=list)
    results: List[SearchResultItem] = Field(default_factory=list)
    raw_snippets_text: str = ""
    provider_used: str = "Tavily Live API"


class ResearchTaskResult(BaseModel):
    """The completed result of an executed research task."""
    task_id: str
    assigned_agent: str
    task_description: str
    status: str = "completed"  # completed, failed
    result: str = ""  # Full markdown synthesis
    queries: List[str] = Field(default_factory=list)
    sources: List[SearchResultItem] = Field(default_factory=list)
    search_provider_used: str = "Tavily Live API"
    key_metrics: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ResearcherConfig(BaseModel):
    """Configuration options for researcher execution, search, and LLM synthesis."""
    model_config = ConfigDict(extra="ignore")

    search_provider: str = "auto"  # auto, tavily, duckduckgo, mock
    tavily_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    llm_provider: str = "groq"
    llm_model: str = "qwen/qwen3.6-27b"
    max_search_results: int = 5
    max_queries_per_task: int = 3
    max_completion_tokens: int = 6144
    timeout_seconds: float = 30.0
