"""Research Brief Agent: converts clarified requests into Supervisor-ready missions."""

from .models import ResearchBrief, ResearchBriefInput, ResearchBriefResult
from .service import ResearchBriefService

__all__ = ["ResearchBrief", "ResearchBriefInput", "ResearchBriefResult", "ResearchBriefService"]
