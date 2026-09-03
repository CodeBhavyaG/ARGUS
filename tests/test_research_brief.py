import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from sih_hackathon.research_brief.config import ResearchBriefConfig
from sih_hackathon.research_brief.models import ResearchBriefInput
from sih_hackathon.research_brief.service import ResearchBriefService
from main import research_brief_node


class ProseLLM:
    async def ainvoke(self, prompt: str) -> str:
        assert "never json" in prompt.lower()
        return "# Research Brief\n\n## Research Question\nHow should cities reduce air pollution?\n\n## Self-Evaluation\nOverall score: 8.5/10."


class TestResearchBrief(unittest.IsolatedAsyncioTestCase):

    async def test_service_returns_plain_language_brief_from_llm(self):
        result = await ResearchBriefService(llm=ProseLLM()).create_brief(
            ResearchBriefInput(request_id="r1", clarified_request="Study city air pollution.")
        )
        self.assertTrue(result.success)
        self.assertTrue(result.brief.startswith("# Research Brief"))
        self.assertFalse(result.brief.lstrip().startswith("{"))

    async def test_offline_fallback_preserves_ambiguity_and_never_researches(self):
        result = await ResearchBriefService(
            config=ResearchBriefConfig(llm_provider="local", llm_api_key=None)
        ).create_brief(ResearchBriefInput(request_id="r2", clarified_request="What is the best energy policy?"))
        self.assertTrue(result.success)
        self.assertIn("## Clarification Needed", result.brief)
        self.assertIn("## Delegation Suggestions", result.brief)

    async def test_node_hands_brief_to_supervisor_contract(self):
        update = await research_brief_node({
            "query": "raw",
            "clarified_request": "Compare electric and hybrid vehicles.",
            "offline": True,
        })
        self.assertEqual(update["research_brief"], update["supervisor_input"])
        self.assertIn("Overall score:", update["brief_self_evaluation"])


if __name__ == "__main__":
    unittest.main()
