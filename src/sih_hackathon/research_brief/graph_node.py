"""State adapter between Clarify Agent output and the Supervisor handoff."""

from typing import Any

from .models import ResearchBriefInput
from .service import ResearchBriefService
from ..state import State


class ResearchBriefNode:
    def __init__(self, llm: Any | None = None, config=None):
        self.service = ResearchBriefService(llm=llm, config=config)

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        current = State(**state)
        clarified_request = current.clarified_request or current.query
        if not clarified_request:
            return {"progress_logs": ["⚠ Cannot create a research brief without a clarified request"], "current_stage": "research_brief"}
        result = await self.service.create_brief(ResearchBriefInput(
            request_id=current.request_id or "research-request", clarified_request=clarified_request,
            original_query=current.query or None, context=current.clarification_context,
            constraints=current.research_constraints, clarification_notes=current.clarification_notes,
        ))
        if not result.success or not result.brief:
            return {"progress_logs": [f"✗ Research brief failed: {result.error}"], "current_stage": "research_brief"}
        return {"research_brief": result.brief, "brief_self_evaluation": result.self_evaluation,
                "supervisor_input": result.brief, "progress_logs": ["✓ Created plain-language research brief for Supervisor"], "current_stage": "research_brief"}
