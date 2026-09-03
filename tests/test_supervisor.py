"""
Unit tests for Supervisor Agent (agent/Superviser.py), State models, and Evaluator.
Run via: python -m unittest discover test
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from state import SupervisorState, ResearchTask
from eval.evaluator import SupervisorEvaluator, VALID_AGENTS
from eval.eval_cases import EVALUATION_CASES


class TestSupervisorPromptAndSetup(unittest.TestCase):
    """Test prompt file integrity and operational rules."""

    def test_prompt_file_exists(self):
        prompt_path = project_root / "prompt" / "Superviser.md"
        self.assertTrue(prompt_path.exists(), "prompt/Superviser.md should exist")
        content = prompt_path.read_text(encoding="utf-8")
        self.assertGreater(len(content), 100, "System prompt should be non-empty")

    def test_prompt_contains_delegation_rules(self):
        prompt_path = project_root / "prompt" / "Superviser.md"
        content = prompt_path.read_text(encoding="utf-8")
        self.assertIn("ResearchAgent_1", content)
        self.assertIn("ResearchAgent_2", content)
        self.assertIn("ResearchAgent_3", content)
        self.assertIn("Strict Load Balancing", content)
        self.assertIn("Anti-Overload Guardrail", content)
        self.assertIn("output_structure", content)


class TestStateModels(unittest.TestCase):
    """Test Pydantic and TypedDict state models."""

    def test_research_task_structure(self):
        task: ResearchTask = {
            "task_description": "Investigate source apportionment PM2.5",
            "assigned_agent": "ResearchAgent_1",
            "status": "pending",
            "result": None,
        }
        self.assertEqual(task["assigned_agent"], "ResearchAgent_1")
        self.assertEqual(task["status"], "pending")
        self.assertIsNone(task["result"])

    def test_supervisor_state_validation(self):
        state = SupervisorState(
            research_brief="Research on urban pollution",
            tasks=[
                {
                    "task_description": "Task 1 description",
                    "assigned_agent": "ResearchAgent_1",
                    "status": "pending",
                    "result": None,
                },
                {
                    "task_description": "Task 2 description",
                    "assigned_agent": "ResearchAgent_2",
                    "status": "pending",
                    "result": None,
                },
            ],
            final_summary=None,
        )
        data = state.model_dump()
        self.assertEqual(data["research_brief"], "Research on urban pollution")
        self.assertEqual(len(data["tasks"]), 2)
        self.assertIsNone(data["final_summary"])


class TestSupervisorEvaluator(unittest.TestCase):
    """Test the evaluation scoring engine and rubric."""

    def setUp(self):
        self.evaluator = SupervisorEvaluator()
        self.sample_brief = """Objective
Provide a comprehensive, evidence-based foundation detailing primary emission sources, atmospheric processes, weather patterns, and public health ramifications of urban air pollution to enable targeted municipal policy design and health interventions.

Scope
• Vehicular emissions and industrial manufacturing
• Meteorological dispersion and temperature inversions
• Public health impacts
• Municipal policy interventions

Delegation Suggestions
• Primary Emission Sources & Source Apportionment: PMF analysis
• Meteorological & Weather Dynamics: Boundary layer height and thermal inversions
• Public Health Impacts & Population Vulnerability: Vulnerable demographics
• Regulatory Policies & Mitigation Interventions: Interventions

Edge Cases and Anomalies
• Thermal Inversion & Stagnant Air Traps
• Low-Cost Sensor Humidity Anomalies

Expected Deliverable
A comprehensive, multi-section research report detailing source attribution estimates and policy effectiveness benchmarks."""

    def test_ideal_supervisor_output_scoring(self):
        ideal_output = {
            "research_brief": self.sample_brief,
            "tasks": [
                {
                    "task_description": "Investigate primary vehicular and industrial emission sources using PMF analysis to quantify proportional contributions to urban air pollution.",
                    "assigned_agent": "ResearchAgent_1",
                    "status": "pending",
                    "result": None,
                },
                {
                    "task_description": "Examine meteorological boundary layer dynamics, thermal temperature inversions, and street canyon dispersion patterns causing localized pollution traps.",
                    "assigned_agent": "ResearchAgent_2",
                    "status": "pending",
                    "result": None,
                },
                {
                    "task_description": "Analyze public health impacts across vulnerable demographics distinguishing toxicological mechanisms of PM0.1 ultrafine particles from PM10 coarse dust.",
                    "assigned_agent": "ResearchAgent_3",
                    "status": "pending",
                    "result": None,
                },
                {
                    "task_description": "Review municipal regulatory interventions including low-emission zones, heavy-duty vehicle restrictions, and sensor humidity calibration anomalies.",
                    "assigned_agent": "ResearchAgent_1",
                    "status": "pending",
                    "result": None,
                },
            ],
            "final_summary": None,
        }
        res = self.evaluator.evaluate(self.sample_brief, ideal_output, case_id="test_01", category="SIMPLE")
        self.assertGreaterEqual(res["overall_score"], 9.0, "Ideal output should score >= 9.0/10")
        self.assertTrue(res["metrics"]["all_agents_utilized"])
        self.assertLessEqual(res["metrics"]["load_delta"], 1)
        self.assertIn("reason", res)
        self.assertGreater(len(res["reason"]), 20)

    def test_penalize_imbalanced_agent_distribution(self):
        imbalanced_output = {
            "research_brief": self.sample_brief,
            "tasks": [
                {
                    "task_description": "Investigate emission sources vehicular industrial PMF",
                    "assigned_agent": "ResearchAgent_1",
                    "status": "pending",
                    "result": None,
                },
                {
                    "task_description": "Examine meteorological dispersion dynamics thermal inversions",
                    "assigned_agent": "ResearchAgent_1",
                    "status": "pending",
                    "result": None,
                },
                {
                    "task_description": "Analyze public health impacts across vulnerable demographics",
                    "assigned_agent": "ResearchAgent_1",
                    "status": "pending",
                    "result": None,
                },
            ],
            "final_summary": None,
        }
        res = self.evaluator.evaluate(self.sample_brief, imbalanced_output, case_id="test_imbalanced")
        # Load balancing score should be penalized because Agent 2 and 3 are idle (load delta = 3)
        self.assertLess(res["dimensions"]["load_balancing"], 2.0)
        self.assertFalse(res["metrics"]["all_agents_utilized"])

    def test_penalize_invalid_agent_names(self):
        invalid_output = {
            "research_brief": self.sample_brief,
            "tasks": [
                {
                    "task_description": "Investigate emission sources",
                    "assigned_agent": "UnregisteredAgent_X",
                    "status": "pending",
                    "result": None,
                }
            ],
            "final_summary": None,
        }
        res = self.evaluator.evaluate(self.sample_brief, invalid_output, case_id="test_invalid")
        self.assertLess(res["dimensions"]["load_balancing"], 1.5)
        self.assertTrue(any("invalid assigned agents" in w.lower() for w in res["weaknesses"]))

    def test_penalize_schema_violations(self):
        bad_schema_output = {
            "research_brief": "",
            "tasks": [
                {
                    "task_description": "Investigate emission sources",
                    "assigned_agent": "ResearchAgent_1",
                    "status": "completed",  # should be pending
                    "result": "Some premature result",  # should be None
                }
            ],
            "final_summary": "Premature summary",  # should be None
        }
        res = self.evaluator.evaluate(self.sample_brief, bad_schema_output, case_id="test_schema")
        self.assertLess(res["dimensions"]["schema_constraints"], 0.8)

    def test_detect_redundant_overlapping_tasks(self):
        redundant_output = {
            "research_brief": self.sample_brief,
            "tasks": [
                {
                    "task_description": "Investigate primary vehicular and industrial emission sources in urban centers.",
                    "assigned_agent": "ResearchAgent_1",
                    "status": "pending",
                    "result": None,
                },
                {
                    "task_description": "Investigate primary vehicular and industrial emission sources in urban centers.",
                    "assigned_agent": "ResearchAgent_2",
                    "status": "pending",
                    "result": None,
                },
                {
                    "task_description": "Analyze public health impacts across vulnerable demographics.",
                    "assigned_agent": "ResearchAgent_3",
                    "status": "pending",
                    "result": None,
                },
            ],
            "final_summary": None,
        }
        res = self.evaluator.evaluate(self.sample_brief, redundant_output, case_id="test_redundant")
        self.assertLess(res["dimensions"]["context_clustering"], 2.5)
        self.assertTrue(any("duplicate" in w.lower() or "overlap" in w.lower() for w in res["weaknesses"]))

    def test_penalize_excessive_task_fragmentation(self):
        fragmented_output = {
            "research_brief": self.sample_brief,
            "tasks": [
                {"task_description": f"Fragmented subtask {i} investigating details", "assigned_agent": f"ResearchAgent_{(i % 3) + 1}", "status": "pending", "result": None}
                for i in range(1, 10)
            ],
            "final_summary": None,
        }
        res = self.evaluator.evaluate(self.sample_brief, fragmented_output, case_id="test_frag")
        self.assertLess(res["dimensions"]["context_clustering"], 1.5)


class TestBenchmarkDataset(unittest.TestCase):
    """Test benchmark evaluation dataset extracted from PDF."""

    def test_dataset_contains_all_7_cases(self):
        self.assertEqual(len(EVALUATION_CASES), 7, "Dataset must contain all 7 test cases from the PDF")

    def test_dataset_case_properties(self):
        expected_ids = {
            "research_001", "research_002", "research_003",
            "research_004", "research_005", "research_006", "research_007"
        }
        actual_ids = {case["id"] for case in EVALUATION_CASES}
        self.assertEqual(expected_ids, actual_ids)

        for case in EVALUATION_CASES:
            self.assertTrue(case["id"])
            self.assertTrue(case["category"])
            self.assertTrue(case["research_query"])
            self.assertTrue(case["research_brief"])
            self.assertIn("Objective", case["research_brief"])
            self.assertIn("Scope", case["research_brief"])
            self.assertIn("Delegation Suggestions", case["research_brief"])
            self.assertIn("Expected Deliverable", case["research_brief"])

    def test_dataset_json_file_sync(self):
        import json
        json_path = project_root / "eval" / "dataset.json"
        self.assertTrue(json_path.exists(), "eval/dataset.json should exist")
        loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(len(loaded_json), len(EVALUATION_CASES))
        self.assertEqual([c["id"] for c in loaded_json], [c["id"] for c in EVALUATION_CASES])


class TestEvaluationPipelineArtifacts(unittest.TestCase):
    """Test generated evaluation report and results structure."""

    def test_evaluation_results_json_schema(self):
        import json
        results_path = project_root / "eval" / "evaluation_results.json"
        self.assertTrue(results_path.exists(), "eval/evaluation_results.json should exist")
        results = json.loads(results_path.read_text(encoding="utf-8"))
        self.assertEqual(len(results), 7, "Should have 7 evaluated cases")

        for entry in results:
            self.assertIn("case_id", entry)
            self.assertIn("overall_score", entry)
            self.assertIn("dimensions", entry)
            self.assertIn("metrics", entry)
            self.assertIn("reason", entry)
            self.assertGreaterEqual(entry["overall_score"], 8.0)

    def test_markdown_report_generation(self):
        from eval.run_eval import generate_markdown_report
        sample_results = [
            {
                "case_id": "research_001",
                "category": "SIMPLE",
                "input_query": "What are causes of air pollution?",
                "overall_score": 10.0,
                "reason": "Decomposed cleanly with load balancing.",
                "dimensions": {
                    "load_balancing": 2.5,
                    "context_clustering": 2.5,
                    "actionability": 2.0,
                    "schema_constraints": 1.5,
                    "scope_coverage": 1.5,
                },
                "metrics": {
                    "task_count": 3,
                    "agent_distribution": {"ResearchAgent_1": 1, "ResearchAgent_2": 1, "ResearchAgent_3": 1},
                    "load_delta": 0,
                    "avg_words_per_task": 55.0,
                },
                "supervisor_output": {
                    "tasks": [
                        {"task_description": "Investigate emission sources", "assigned_agent": "ResearchAgent_1", "status": "pending"}
                    ]
                },
                "strengths": ["Balanced load"],
                "weaknesses": [],
            }
        ]
        md_text = generate_markdown_report(sample_results, 10.0)
        self.assertIn("# Supervisor Agent — Evaluation Report", md_text)
        self.assertIn("research_001", md_text)
        self.assertIn("10.0", md_text)


class TestSupervisorAgentIntegration(unittest.TestCase):
    """Test Supervisor Agent module import and execution functions."""

    def test_create_supervisor_agent_function(self):
        from agent.Superviser import create_supervisor_agent, get_system_prompt
        prompt = get_system_prompt()
        self.assertIn("Supervisor Agent", prompt)

    def test_run_supervisor_mocked(self):
        from agent.Superviser import run_supervisor
        
        mock_agent = MagicMock()
        mock_response = SupervisorState(
            research_brief="Mock Brief",
            tasks=[
                {
                    "task_description": "Mock research task 1",
                    "assigned_agent": "ResearchAgent_1",
                    "status": "pending",
                    "result": None,
                },
                {
                    "task_description": "Mock research task 2",
                    "assigned_agent": "ResearchAgent_2",
                    "status": "pending",
                    "result": None,
                },
            ],
            final_summary=None,
        )
        mock_agent.invoke.return_value = {"structured_response": mock_response}

        result = run_supervisor("Test input brief", supervisor_agent=mock_agent)
        self.assertIsInstance(result, SupervisorState)
        self.assertEqual(len(result.tasks), 2)
        self.assertEqual(result.tasks[0]["assigned_agent"], "ResearchAgent_1")


if __name__ == "__main__":
    unittest.main()
