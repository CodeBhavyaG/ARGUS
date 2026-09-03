"""Structured contracts for the Research Brief Agent."""

from typing import Literal

from pydantic import BaseModel, Field


class ResearchTask(BaseModel):
    """A research unit the Supervisor may delegate; it is not an execution command."""

    task_id: str
    title: str
    objective: str
    research_questions: list[str] = Field(default_factory=list)
    research_area: str
    evidence_requirements: list[str] = Field(default_factory=list)
    suggested_researcher_type: str = "domain researcher"
    priority: Literal["high", "medium", "low"] = "medium"


class ResearchBrief(BaseModel):
    """The planning handoff from Clarify Agent to Supervisor Agent."""

    research_question: str
    objective: str
    scope_included: list[str] = Field(default_factory=list)
    scope_excluded: list[str] = Field(default_factory=list)
    key_questions: list[str] = Field(default_factory=list)
    research_areas: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    suggested_research_tasks: list[ResearchTask] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)
    expected_deliverable: str
    evaluation_criteria: list[str] = Field(default_factory=list)
    priority: Literal["high", "medium", "low"] = "medium"
    confidence: Literal["high", "medium", "low"] = "medium"
    assumptions: list[str] = Field(default_factory=list)
    clarification_needed: list[str] = Field(default_factory=list)


class BriefEvaluationDimensions(BaseModel):
    question_clarity: float = Field(ge=0, le=10)
    scope_definition: float = Field(ge=0, le=10)
    completeness: float = Field(ge=0, le=10)
    research_decomposition: float = Field(ge=0, le=10)
    task_quality: float = Field(ge=0, le=10)
    evidence_requirements: float = Field(ge=0, le=10)
    relevance: float = Field(ge=0, le=10)
    downstream_research_potential: float = Field(ge=0, le=10)
    ambiguity_remaining: float = Field(ge=0, le=10, description="10 means ambiguity is well handled/minimal.")


class BriefSelfEvaluation(BaseModel):
    overall_score: float = Field(ge=0, le=10)
    dimensions: BriefEvaluationDimensions
    reasoning: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)


class ResearchBriefInput(BaseModel):
    """Input supplied after clarification, before any research execution."""

    request_id: str
    clarified_request: str = Field(min_length=1)
    original_query: str | None = None
    context: str | None = None
    constraints: list[str] = Field(default_factory=list)
    clarification_notes: list[str] = Field(default_factory=list)


class ResearchBriefResult(BaseModel):
    """Plain-language handoff. The public agent output is intentionally not JSON."""

    request_id: str
    brief: str = ""
    self_evaluation: str = ""
    success: bool = True
    error: str | None = None
