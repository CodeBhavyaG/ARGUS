"""Main CLI entrypoint to execute the Research Brief Agent -> Supervisor Agent -> Research Agents pipeline via LangGraph."""
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
from agent.ResearchAgent import run_all_research_tasks
from sih_hackathon.utils.pdf_exporter import export_pipeline_to_pdf


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
                "task_description": "Conduct quantitative source apportionment and receptor modeling across vehicular exhaust, tire wear, and point-source industrial emissions.",
                "assigned_agent": "ResearchAgent_1",
                "status": "pending",
                "result": None,
            },
            {
                "task_id": "task_2",
                "task_description": "Investigate meteorological boundary layer dynamics, thermal temperature inversions, and street canyon dispersion patterns causing localized pollution traps.",
                "assigned_agent": "ResearchAgent_2",
                "status": "pending",
                "result": None,
            },
            {
                "task_id": "task_3",
                "task_description": "Evaluate public health epidemiology across vulnerable cohorts and assess empirical effectiveness of urban low emission zones and industrial fuel switching.",
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


async def research_execution_node(state: ResearchGraphState) -> dict:
    """Execute all research tasks concurrently via Research Agents."""
    tasks = state.get("tasks", [])
    offline = state.get("offline", False)
    
    if not tasks:
        return {"tasks": [], "progress_logs": state.get("progress_logs", []) + ["⚠ No tasks to execute"]}

    completed_tasks = await run_all_research_tasks(tasks, offline=offline)
    
    return {
        "tasks": completed_tasks,
        "progress_logs": state.get("progress_logs", []) + [
            f"✓ Research Agents executed and synthesized {len(completed_tasks)} empirical research tasks"
        ]
    }


def build_pipeline():
    workflow = StateGraph(ResearchGraphState)
    workflow.add_node("research_brief", research_brief_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("research_execution", research_execution_node)
    
    workflow.add_edge(START, "research_brief")
    workflow.add_edge("research_brief", "supervisor")
    workflow.add_edge("supervisor", "research_execution")
    workflow.add_edge("research_execution", END)
    
    return workflow.compile()


pipeline = build_pipeline()


async def run_pipeline(
    query: str,
    context: str = "",
    offline: bool = False,
    output_file: str | None = None,
    pdf_file: str | None = None,
) -> dict:
    mode_label = "OFFLINE DETERMINISTIC BLUEPRINT" if offline else "LIVE GROQ / SEARCH API"
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
    print("📄 1. PUBLIC RESEARCH BRIEF (Supervisor Ingestion)")
    print("=" * 80)
    print(final_state.get("research_brief", "No brief generated."))

    print("\n" + "=" * 80)
    print("🎯 2. SUPERVISOR DELEGATION PLAN")
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

    print("\n" + "=" * 80)
    print("🔬 3. RESEARCH EXECUTION FINDINGS (By Specialized Research Agents)")
    print("=" * 80)
    for i, t in enumerate(tasks, 1):
        print(f"\n{'=' * 40}")
        print(f"[{t.get('task_id', f'task_{i}')}] — {t.get('assigned_agent')} (Status: {t.get('status')})")
        print(f"{'=' * 40}")
        print(t.get("result", "*No findings recorded.*"))
        sources = t.get("sources", [])
        if sources:
            print(f"\n[Cited Sources Count: {len(sources)}]")

    if final_state.get("brief_self_evaluation"):
        print("\n" + "=" * 80)
        print("🔍 4. INTERNAL DEVELOPER DIAGNOSTIC (Private Self-Evaluation)")
        print("=" * 80)
        print(final_state.get("brief_self_evaluation"))

    # Handle PDF export
    effective_pdf = pdf_file or (output_file if output_file and output_file.endswith(".pdf") else None)
    if effective_pdf:
        pdf_path = export_pipeline_to_pdf(final_state, effective_pdf)
        print(f"\n📄 [Generated Systematic PDF Report]: {pdf_path}")

    # Handle Text / JSON output export
    if output_file and not output_file.endswith(".pdf"):
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
                sources_count = len(t.get('sources', []))
                task_lines.append(
                    f"[{t.get('task_id', f'task_{i}')}] -> ASSIGNED TO: {t.get('assigned_agent')}\n"
                    f"Status: {t.get('status', 'pending')} | Sources: {sources_count}\n"
                    f"Description:\n{t.get('task_description')}\n\n"
                    f"Findings:\n{t.get('result')}"
                )
            text_content = (
                f"# MULTI-AGENT RESEARCH PIPELINE OUTPUT\n"
                f"Mode: {mode_label}\n"
                f"Query: {query}\n"
                f"Context: {context or 'None'}\n"
                f"{'=' * 80}\n\n"
                f"## 1. PUBLIC RESEARCH BRIEF\n\n"
                f"{final_state.get('research_brief', 'None')}\n\n"
                f"{'=' * 80}\n\n"
                f"## 2. SUPERVISOR DELEGATION & RESEARCH RESULTS\n\n"
                f"Total Tasks: {len(tasks)}\n"
                f"Agent Load Distribution: {json.dumps(agent_counts)}\n\n"
                + "\n\n" + ("=" * 40 + "\n\n").join(task_lines)
                + f"\n\n{'=' * 80}\n\n"
                + f"## 3. INTERNAL DEVELOPER DIAGNOSTIC\n\n"
                + f"{final_state.get('brief_self_evaluation', 'None')}"
            )
            out_path.write_text(text_content.strip() + "\n", encoding="utf-8")
        print(f"\n[Saved Text/JSON Output]: {out_path}")

    print("\n" + "=" * 80 + "\n")
    return final_state


def main():
    parser = argparse.ArgumentParser(description="Run the Research Brief -> Supervisor -> Researcher LangGraph Pipeline.")
    parser.add_argument(
        "query",
        nargs="?",
        default="What are the major causes of urban air pollution?",
        help="Research query / topic",
    )
    parser.add_argument("--context", default="A city public-health team needs a neutral overview.", help="Optional context")
    parser.add_argument("--offline", action="store_true", help="Run in offline mode using deterministic domain blueprints")
    parser.add_argument("--output", "-o", default=None, help="Path to save output (.txt, .json, or .pdf)")
    parser.add_argument("--pdf", default=None, nargs="?", const="ARGUS_Research_Dossier.pdf", help="Generate a systematic publication-ready PDF report (e.g. --pdf report.pdf)")
    args = parser.parse_args()

    asyncio.run(run_pipeline(args.query, args.context, args.offline, args.output, args.pdf))


if __name__ == "__main__":
    main()
