"""Research Brief Agent implementation in agent/ directory."""
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env", override=False)

from sih_hackathon.research_brief.models import ResearchBriefInput, ResearchBriefResult
from sih_hackathon.research_brief.service import ResearchBriefService
from sih_hackathon.research_brief.config import ResearchBriefConfig


def get_system_prompt() -> str:
    """Load the Research Brief system prompt from prompt/ResearchBrief.md."""
    prompt_path = project_root / "prompt" / "ResearchBrief.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    return "You are the Research Brief Agent in a multi-agent research system."


def create_brief_service(llm=None, config=None, offline: bool = False) -> ResearchBriefService:
    """Initialize and return the ResearchBriefService instance."""
    if offline:
        cfg = config or ResearchBriefConfig(llm_provider="local", llm_api_key=None)
    else:
        cfg = config or ResearchBriefConfig()
    return ResearchBriefService(llm=llm, config=cfg)


async def run_research_brief(
    query: str,
    context: str | None = None,
    offline: bool = False,
    request_id: str = "brief-request",
) -> ResearchBriefResult:
    """
    Execute the Research Brief Agent to produce a structured, plain-language research brief.
    """
    service = create_brief_service(offline=offline)
    return await service.create_brief(ResearchBriefInput(
        request_id=request_id,
        clarified_request=query,
        original_query=query,
        context=context,
    ))


if __name__ == "__main__":
    import asyncio
    query = "What are the major causes of urban air pollution?"
    result = asyncio.run(run_research_brief(query, offline=True))
    print(f"Success: {result.success}")
    print("\n--- BRIEF ---")
    print(result.brief)
    print("\n--- SELF-EVALUATION ---")
    print(result.self_evaluation)
