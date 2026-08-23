from pydantic import BaseModel
from typing_extensions import TypedDict


class State(BaseModel):
    """
    State class to represent the state of the application.
    """

    query: str


class ResearchTask(TypedDict):
    task_description: str
    assigned_agent: str
    status: str
    result: str | None


class SupervisorState(BaseModel):
    research_brief: str
    tasks: list[ResearchTask] = []
    final_summary: str | None = None