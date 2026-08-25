"""
Unit tests for the Research Agent (agent/ResearchAgent.py) and research service layer.
Run via: pytest tests/test_research_agent.py
"""
import pytest
import asyncio
from pathlib import Path

from sih_hackathon.researcher.models import ResearcherConfig, ResearchEvidence, SearchResultItem
from sih_hackathon.researcher.tools import search_offline_knowledge, execute_web_search
from sih_hackathon.researcher.service import ResearcherService, get_researcher_system_prompt
from agent.ResearchAgent import run_single_research_task, run_all_research_tasks
from main import research_execution_node, build_pipeline


@pytest.mark.asyncio
async def test_researcher_prompt_exists():
    prompt = get_researcher_system_prompt()
    assert len(prompt) > 100
    assert "Zero Hallucination" in prompt
    assert "Executive Summary" in prompt
    assert "Verified Sources & Citations" in prompt


@pytest.mark.asyncio
async def test_offline_knowledge_search():
    results = search_offline_knowledge("urban PM2.5 air pollution vehicular emissions", max_results=3)
    assert len(results) > 0
    assert any("epa.gov" in r.url or "nature.com" in r.url for r in results)
    assert all(r.title and r.snippet for r in results)


@pytest.mark.asyncio
async def test_query_planning_generates_multi_vector_queries():
    service = ResearcherService()
    task_desc = "Investigate receptor modeling and PMF 5.0 source apportionment across vehicular exhaust and tire wear."
    queries = service.plan_queries(task_desc)
    assert len(queries) >= 2
    assert any("source apportionment" in q.lower() or "pmf" in q.lower() or "vehicular" in q.lower() for q in queries)


@pytest.mark.asyncio
async def test_single_task_execution_offline():
    task = {
        "task_id": "task_1",
        "task_description": "Conduct quantitative source apportionment across primary combustion sources.",
        "assigned_agent": "ResearchAgent_1",
        "status": "pending",
        "result": None,
    }
    updated = await run_single_research_task(task, offline=True)
    assert updated["status"] == "completed"
    assert updated["result"] is not None
    assert "## 1. Executive Summary" in updated["result"]
    assert "## 2. Key Findings & Empirical Evidence" in updated["result"]
    assert "## 5. Verified Sources & Citations" in updated["result"]
    assert len(updated.get("sources", [])) > 0


@pytest.mark.asyncio
async def test_batch_parallel_execution():
    tasks = [
        {
            "task_id": f"task_{i}",
            "task_description": f"Investigate research sub-domain {i} with empirical datasets.",
            "assigned_agent": f"ResearchAgent_{i}",
            "status": "pending",
            "result": None,
        }
        for i in range(1, 4)
    ]
    completed = await run_all_research_tasks(tasks, offline=True)
    assert len(completed) == 3
    for t in completed:
        assert t["status"] == "completed"
        assert t["result"] and len(t["result"]) > 100


@pytest.mark.asyncio
async def test_research_execution_node_in_graph():
    state = {
        "tasks": [
            {
                "task_id": "task_1",
                "task_description": "Analyze meteorological thermal inversions.",
                "assigned_agent": "ResearchAgent_2",
                "status": "pending",
                "result": None,
            }
        ],
        "offline": True,
        "progress_logs": [],
    }
    update = await research_execution_node(state)
    assert len(update["tasks"]) == 1
    assert update["tasks"][0]["status"] == "completed"
    assert any("Research Agents executed" in log for log in update["progress_logs"])


@pytest.mark.asyncio
async def test_full_pipeline_compilation_and_offline_execution():
    compiled_app = build_pipeline()
    initial_state = {
        "query": "What are the major causes of urban air pollution?",
        "offline": True,
    }
    final_state = await compiled_app.ainvoke(initial_state)
    assert "research_brief" in final_state
    assert len(final_state.get("tasks", [])) == 3
    for task in final_state["tasks"]:
        assert task["status"] == "completed"
        assert task["result"] is not None
        assert "Verified Sources" in task["result"]
