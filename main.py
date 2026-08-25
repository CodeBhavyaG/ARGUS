"""Main CLI entrypoint to execute the Research Brief Agent -> Supervisor Agent pipeline via LangGraph."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure root and src are in path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

from langgraph.graph import StateGraph, START, END
from state import ResearchGraphState
from agent.ResearchBrief import run_research_brief
from agent.Superviser import run_supervisor, SupervisorState


async def research_brief_node(state: ResearchGraphState) -> dict:
    query = state.get("clarified_request") or state.get("query") or ""
    context = state.get("context") or None
    offline = state.get("offline", False)

    result = await run_research_brief(query=query, context=context, offline=offline)

    mode_label = "offline domain blueprint" if offline else "live model"
    return {
        "research_brief": result.brief,
        "brief_self_evaluation": result.self_evaluation,
        "supervisor_input": result.brief,
        "progress_logs": state.get("progress_logs", []) + [f"✓ Research Brief Agent created brief ({mode_label})"]
    }


async def supervisor_node(state: ResearchGraphState) -> dict:
    brief = state.get("research_brief", "")
    offline = state.get("offline", False)
    
    if not brief:
        return {"tasks": [], "progress_logs": state.get("progress_logs", []) + ["⚠ Empty research brief"]}

    if offline:
        # Deterministic offline decomposition
        tasks = [
            {
                "task_id": "task_1",
                "task_description": "Conduct quantitative source apportionment and emission inventory analysis across primary combustion sources.",
                "assigned_agent": "ResearchAgent_1",
                "status": "pending",
                "result": None,
            },
            {
                "task_id": "task_2",
                "task_description": "Investigate atmospheric chemistry, secondary photochemical formation, and meteorological inversion trapping.",
                "assigned_agent": "ResearchAgent_2",
                "status": "pending",
                "result": None,
            },
            {
                "task_id": "task_3",
                "task_description": "Evaluate regulatory frameworks, municipal compliance enforcement, socio-economic exposure equity, and emerging sources.",
                "assigned_agent": "ResearchAgent_3",
                "status": "pending",
                "result": None,
            },
        ]
        return {
            "tasks": tasks,
            "final_summary": None,
            "progress_logs": state.get("progress_logs", []) + ["✓ Supervisor Agent decomposed brief into 3 balanced missions (offline)"]
        }

    try:
        sup_state = run_supervisor(brief)
        tasks_data = [t if isinstance(t, dict) else t.model_dump() for t in sup_state.tasks]
        return {
            "tasks": tasks_data,
            "final_summary": sup_state.final_summary,
            "progress_logs": state.get("progress_logs", []) + [f"✓ Supervisor Agent decomposed brief into {len(tasks_data)} balanced missions (live)"]
        }
    except Exception as exc:
        return {
            "tasks": [],
            "progress_logs": state.get("progress_logs", []) + [f"✗ Supervisor Agent error: {exc}"]
        }


def build_pipeline():
    workflow = StateGraph(ResearchGraphState)
    workflow.add_node("research_brief", research_brief_node)
    workflow.add_node("supervisor", supervisor_node)
    
    workflow.add_edge(START, "research_brief")
    workflow.add_edge("research_brief", "supervisor")
    workflow.add_edge("supervisor", END)
    
    return workflow.compile()


pipeline = build_pipeline()


async def run_pipeline(
    query: str,
    context: str = "",
    offline: bool = False,
    output_file: str | None = None,
) -> dict:
    mode_label = "OFFLINE DETERMINISTIC BLUEPRINT" if offline else "LIVE GROQ API"
    print("\n" + "=" * 80)
    print("🚀 EXECUTING MULTI-AGENT RESEARCH PIPELINE (LangGraph)")
    print(f"MODE   : {mode_label}")
    print(f"QUERY  : {query}")
    print(f"CONTEXT: {context or 'None'}")
    print("=" * 80 + "\n")

    initial_state = {
        "query": query,
        "clarified_request": query,
        "context": context or None,
        "offline": offline,
        "progress_logs": [],
    }

    final_state = await pipeline.ainvoke(initial_state)

    print("\n[PROGRESS LOGS]:")
    for log in final_state.get("progress_logs", []):
        print(f"  {log}")

    print("\n" + "=" * 80)
    print("📄 1. PUBLIC RESEARCH BRIEF (Passed to Supervisor Agent)")
    print("=" * 80)
    print(final_state.get("research_brief", "No brief generated."))

    print("\n" + "=" * 80)
    print("🎯 2. SUPERVISOR DELEGATION PLAN (Decomposed across Research Agents)")
    print("=" * 80)
    tasks = final_state.get("tasks", [])
    agent_counts = {}
    if not tasks:
        print("No tasks generated by Supervisor.")
    else:
        for t in tasks:
            agent = t.get("assigned_agent", "Unassigned")
            agent_counts[agent] = agent_counts.get(agent, 0) + 1

        print(f"\nTotal Tasks: {len(tasks)}")
        print("Agent Load Distribution:")
        for agent, count in sorted(agent_counts.items()):
            print(f"  • {agent}: {count} tasks")

        print("\nDetailed Task Allocations:")
        for i, t in enumerate(tasks, 1):
            print(f"\n[{t.get('task_id', f'task_{i}')}] -> ASSIGNED TO: {t.get('assigned_agent')}")
            print(f"Status: {t.get('status', 'pending')}")
            print(f"Description:\n{t.get('task_description')}")

    if final_state.get("brief_self_evaluation"):
        print("\n" + "=" * 80)
        print("🔍 3. INTERNAL DEVELOPER DIAGNOSTIC (Private Self-Evaluation)")
        print("=" * 80)
        print(final_state.get("brief_self_evaluation"))

    if output_file:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if str(out_path).endswith(".json"):
            out_data = {
                "mode": mode_label,
                "query": query,
                "context": context,
                "public_research_brief": final_state.get("research_brief"),
                "tasks": final_state.get("tasks"),
                "agent_distribution": agent_counts,
                "internal_self_evaluation": final_state.get("brief_self_evaluation"),
            }
            out_path.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
        else:
            task_lines = []
            for i, t in enumerate(tasks, 1):
                task_lines.append(
                    f"[{t.get('task_id', f'task_{i}')}] -> ASSIGNED TO: {t.get('assigned_agent')}\n"
                    f"Status: {t.get('status', 'pending')}\n"
                    f"Description:\n{t.get('task_description')}"
                )
            text_content = (
                f"# MULTI-AGENT RESEARCH PIPELINE OUTPUT\n"
                f"Mode: {mode_label}\n"
                f"Query: {query}\n"
                f"Context: {context or 'None'}\n"
                f"{'=' * 80}\n\n"
                f"## 1. PUBLIC RESEARCH BRIEF (Supervisor Ingestion)\n\n"
                f"{final_state.get('research_brief', 'None')}\n\n"
                f"{'=' * 80}\n\n"
                f"## 2. SUPERVISOR DELEGATION PLAN\n\n"
                f"Total Tasks: {len(tasks)}\n"
                f"Agent Load Distribution: {json.dumps(agent_counts)}\n\n"
                + "\n\n".join(task_lines)
                + f"\n\n{'=' * 80}\n\n"
                + f"## 3. INTERNAL DEVELOPER DIAGNOSTIC (Self-Evaluation)\n\n"
                + f"{final_state.get('brief_self_evaluation', 'None')}"
            )
            out_path.write_text(text_content.strip() + "\n", encoding="utf-8")
        print(f"\n[Saved Output]: {out_path}")

    print("\n" + "=" * 80 + "\n")
    return final_state


def main():
    parser = argparse.ArgumentParser(description="Run the Research Brief -> Supervisor LangGraph Pipeline.")
    parser.add_argument(
        "query",
        nargs="?",
        default="What are the major causes of urban air pollution?",
        help="Research query / topic",
    )
    parser.add_argument("--context", default="A city public-health team needs a neutral overview.", help="Optional context")
    parser.add_argument("--offline", action="store_true", help="Run in offline mode using deterministic domain blueprints")
    parser.add_argument("--output", "-o", default=None, help="Path to save output (.txt or .json)")
    args = parser.parse_args()

    asyncio.run(run_pipeline(args.query, args.context, args.offline, args.output))


if __name__ == "__main__":
    main()
