"""Research Agent runner and executor in the agent/ directory."""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env", override=False)

from sih_hackathon.researcher.models import ResearcherConfig, ResearchTaskResult
from sih_hackathon.researcher.service import ResearcherService, get_researcher_system_prompt


def create_researcher_service(config: Optional[ResearcherConfig] = None, llm=None, offline: bool = False) -> ResearcherService:
    """Factory to initialize ResearcherService with configuration."""
    cfg = config or ResearcherConfig()
    return ResearcherService(config=cfg, llm=llm)


async def run_single_research_task(
    task: Dict[str, Any],
    offline: bool = False,
    config: Optional[ResearcherConfig] = None,
    llm=None,
) -> Dict[str, Any]:
    """
    Execute a single research task through the Research Agent and return updated task dict.
    """
    service = create_researcher_service(config=config, llm=llm, offline=offline)
    task_res: ResearchTaskResult = await service.execute_task(task, offline=offline)
    
    # Return updated dictionary adhering to state.ResearchTask
    return {
        "task_id": task_res.task_id,
        "task_description": task_res.task_description,
        "assigned_agent": task_res.assigned_agent,
        "status": task_res.status,
        "result": task_res.result,
        "queries": task_res.queries,
        "search_provider_used": task_res.search_provider_used,
        "sources": [s.model_dump() for s in task_res.sources],
    }


async def run_all_research_tasks(
    tasks: List[Dict[str, Any]],
    offline: bool = False,
    config: Optional[ResearcherConfig] = None,
) -> List[Dict[str, Any]]:
    """
    Execute multiple research tasks concurrently using asyncio.gather.
    """
    if not tasks:
        return []

    service = create_researcher_service(config=config, offline=offline)
    execution_coroutines = [
        service.execute_task(task, offline=offline)
        for task in tasks
    ]
    
    task_results = await asyncio.gather(*execution_coroutines)
    
    updated_tasks = []
    for res in task_results:
        updated_tasks.append({
            "task_id": res.task_id,
            "task_description": res.task_description,
            "assigned_agent": res.assigned_agent,
            "status": res.status,
            "result": res.result,
            "queries": res.queries,
            "search_provider_used": res.search_provider_used,
            "sources": [s.model_dump() for s in res.sources],
        })
    return updated_tasks


if __name__ == "__main__":
    sample_task = {
        "task_id": "task_1",
        "task_description": "Investigate positive matrix factorization and source apportionment of PM2.5 in urban centers.",
        "assigned_agent": "ResearchAgent_1",
        "status": "pending",
        "result": None,
    }
    print("Testing Research Agent (Offline mode)...")
    res = asyncio.run(run_single_research_task(sample_task, offline=True))
    print(f"Status: {res['status']}")
    print(f"Sources found: {len(res.get('sources', []))}")
    print("\n--- RESEARCH RESULT ---")
    print(res["result"])
