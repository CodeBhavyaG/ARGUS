import pytest

from sih_hackathon.research_brief.config import ResearchBriefConfig
from sih_hackathon.research_brief.graph_node import ResearchBriefNode
from sih_hackathon.research_brief.models import ResearchBriefInput
from sih_hackathon.research_brief.service import ResearchBriefService


class ProseLLM:
    async def ainvoke(self, prompt: str) -> str:
        assert "never json" in prompt.lower()
        return "# Research Brief\n\n## Research Question\nHow should cities reduce air pollution?\n\n## Self-Evaluation\nOverall score: 8.5/10."


@pytest.mark.asyncio
async def test_service_returns_plain_language_brief_from_llm():
    result = await ResearchBriefService(llm=ProseLLM()).create_brief(ResearchBriefInput(request_id="r1", clarified_request="Study city air pollution."))
    assert result.success and result.brief.startswith("# Research Brief")
    assert not result.brief.lstrip().startswith("{")


@pytest.mark.asyncio
async def test_offline_fallback_preserves_ambiguity_and_never_researches():
    result = await ResearchBriefService(config=ResearchBriefConfig(llm_provider="local", llm_api_key=None)).create_brief(ResearchBriefInput(request_id="r2", clarified_request="What is the best energy policy?"))
    assert result.success and "## Clarification Needed" in result.brief
    assert "## Delegation Suggestions" in result.brief


@pytest.mark.asyncio
async def test_node_hands_brief_to_supervisor_contract():
    update = await ResearchBriefNode(config=ResearchBriefConfig(llm_provider="local", llm_api_key=None)).execute({"request_id": "r3", "query": "raw", "clarified_request": "Compare electric and hybrid vehicles."})
    assert update["research_brief"] == update["supervisor_input"]
    assert "Overall score:" in update["brief_self_evaluation"]
