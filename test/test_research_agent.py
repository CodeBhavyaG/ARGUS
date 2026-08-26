import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.ResearchAgent import (
    ResearchAgent,
    ResearchAgentConfig,
    ResearchTaskInput,
    ResearchTaskResult,
    run_research_agents,
)
from main import research_execution_node


class MockWorkerLLM:
    def __init__(self, output_text: str = ""):
        self.output_text = output_text or (
            "### 1. Executive Summary\nEmpirical investigation completed.\n\n"
            "### 2. Key Findings & Empirical Evidence\n- Baseline energy density: 450 Wh/kg.\n\n"
            "### 3. Methodological Nuances & Contradictions\n- Variance across cell formats.\n\n"
            "### 4. Key Takeaways & Downstream Implications\n- Suitable for regional electric aviation.\n\n"
            "### 5. Verified Sources & Citations\n- FAA Tech Center Report 2024\n- Nature Energy Vol 9"
        )

    async def ainvoke(self, prompt: str) -> str:
        return self.output_text


class TestResearchAgent(unittest.IsolatedAsyncioTestCase):

    async def test_offline_execution_produces_5_sections(self):
        agent = ResearchAgent(agent_id="ResearchAgent_1")
        task_input = ResearchTaskInput(
            task_id="task_1",
            task_description="Analyze energy density and power delivery for solid-state batteries.",
            assigned_agent="ResearchAgent_1",
            research_brief="# Brief\nCompare solid-state batteries vs lithium-ion.",
        )
        res = await agent.execute_task(task_input, offline=True)
        self.assertTrue(res.success)
        self.assertEqual(res.status, "COMPLETED")
        self.assertIn("1. Executive Summary", res.findings)
        self.assertIn("2. Key Findings & Empirical Evidence", res.findings)
        self.assertIn("3. Methodological Nuances & Contradictions", res.findings)
        self.assertIn("4. Key Takeaways & Downstream Implications", res.findings)
        self.assertIn("5. Verified Sources & Citations", res.findings)
        self.assertTrue(len(res.sources) >= 1)

    async def test_mock_llm_execution(self):
        agent = ResearchAgent(agent_id="ResearchAgent_2", llm=MockWorkerLLM())
        task_input = ResearchTaskInput(
            task_id="task_2",
            task_description="Investigate thermal runaway thresholds and flammability.",
            assigned_agent="ResearchAgent_2",
            research_brief="# Brief",
        )
        res = await agent.execute_task(task_input, offline=False)
        self.assertTrue(res.success)
        self.assertEqual(res.status, "COMPLETED")
        self.assertIn("450 Wh/kg", res.findings)
        self.assertIn("FAA Tech Center Report 2024", res.sources)

    async def test_run_research_agents_parallel_dispatch(self):
        tasks = [
            {
                "task_id": "task_1",
                "task_description": "Analyze specific energy and density metrics.",
                "assigned_agent": "ResearchAgent_1",
                "status": "pending",
                "result": None,
            },
            {
                "task_id": "task_2",
                "task_description": "Evaluate safety profiles and thermal runaway.",
                "assigned_agent": "ResearchAgent_2",
                "status": "pending",
                "result": None,
            },
            {
                "task_id": "task_3",
                "task_description": "Investigate manufacturing scalability and supply chain.",
                "assigned_agent": "ResearchAgent_3",
                "status": "pending",
                "result": None,
            },
        ]
        brief = "# Master Brief on Battery Architectures"
        results = await run_research_agents(tasks, brief=brief, offline=True)

        self.assertEqual(len(results), 3)
        for r in results:
            self.assertEqual(r["status"], "COMPLETED")
            self.assertIsNotNone(r["result"])
            self.assertIn("Executive Summary", r["result"])
            self.assertTrue(len(r["sources"]) >= 1)

    async def test_research_execution_node_in_graph(self):
        initial_state = {
            "query": "Compare solid-state batteries vs lithium-ion batteries",
            "research_brief": "# Brief",
            "tasks": [
                {
                    "task_id": "task_1",
                    "task_description": "Assess lifecycle emissions and recycling.",
                    "assigned_agent": "ResearchAgent_1",
                    "status": "pending",
                    "result": None,
                }
            ],
            "offline": True,
            "progress_logs": [],
        }
        update = await research_execution_node(initial_state)
        self.assertEqual(len(update["tasks"]), 1)
        self.assertEqual(update["tasks"][0]["status"], "COMPLETED")
        self.assertIn("Executive Summary", update["tasks"][0]["result"])


if __name__ == "__main__":
    unittest.main()
