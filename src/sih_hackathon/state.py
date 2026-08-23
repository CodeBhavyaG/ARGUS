from typing import Any, Dict, List

from pydantic import BaseModel, Field, ConfigDict


class TodoItem(BaseModel):
    """A single task item in the project workflow."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    intent: str
    query: str
    status: str = "pending"
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    sources: List[str] = Field(default_factory=list)


class State(BaseModel):
    """Shared state at the clarification → briefing → supervision boundary."""

    model_config = ConfigDict(extra="allow")

    # Retained for compatibility with any already-wired downstream task executor.
    todos: List[TodoItem] = Field(default_factory=list)
    completed_todos: List[TodoItem] = Field(default_factory=list)
    task_summaries: Dict[str, str] = Field(default_factory=dict)
    progress_logs: List[str] = Field(default_factory=list)
    current_stage: str = "idle"
    request_id: str = ""
    query: str = ""
    clarified_request: str = ""
    clarification_context: str = ""
    clarification_notes: List[str] = Field(default_factory=list)
    research_constraints: List[str] = Field(default_factory=list)
    research_brief: str = ""
    brief_self_evaluation: str = ""
    # Explicit payload consumed by the future/external Supervisor Agent.
    supervisor_input: str = ""
