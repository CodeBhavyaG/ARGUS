from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, ConfigDict, Field


class ResearchTask(TypedDict, total=False):
    task_id: str
    task_description: str
    assigned_agent: str
    status: str
    result: Optional[str]
    sources: Optional[List[Dict[str, Any]]]


class SupervisorState(BaseModel):
    research_brief: str
    tasks: List[ResearchTask] = Field(default_factory=list)
    final_summary: Optional[str] = None


class ResearchGraphState(TypedDict, total=False):
    query: str
    clarified_request: Optional[str]
    context: Optional[str]
    research_brief: Optional[str]
    brief_self_evaluation: Optional[str]
    supervisor_input: Optional[str]
    tasks: List[ResearchTask]
    final_summary: Optional[str]
    progress_logs: List[str]
    offline: bool


class State(BaseModel):
    """Pydantic state model for validation and backward-compatibility."""
    model_config = ConfigDict(extra="allow")

    request_id: str = ""
    query: str = ""
    clarified_request: str = ""
    clarification_context: str = ""
    clarification_notes: List[str] = Field(default_factory=list)
    research_constraints: List[str] = Field(default_factory=list)
    research_brief: str = ""
    brief_self_evaluation: str = ""
    supervisor_input: str = ""
    tasks: List[ResearchTask] = Field(default_factory=list)
    final_summary: Optional[str] = None
    progress_logs: List[str] = Field(default_factory=list)