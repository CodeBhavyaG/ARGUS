"""Main CLI entrypoint to execute the full ARGUS Multi-Agent Research Pipeline via LangGraph.

Pipeline Flow:
  START -> Research Brief Agent -> Supervisor Agent -> Research Agents -> END
"""

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
from agent.Superviser import run_supervisor
from agent.ResearchAgent import run_research_agents


async def research_brief_node(state: ResearchGraphState) -> dict:
    query = state.get("clarified_request") or state.get("query") or ""
    context = state.get("context") or None
    offline = state.get("offline", False)

    print("\n[STAGE 1/3] Research Brief Agent generating comprehensive research plan...")
    result = await run_research_brief(query=query, context=context, offline=offline)

    mode_label = "offline domain blueprint" if offline else "live model"
    print(f"  ✓ Brief created successfully ({mode_label})")
    return {
        "research_brief": result.brief,
        "brief_self_evaluation": result.self_evaluation,
        "supervisor_input": result.brief,
        "progress_logs": state.get("progress_logs", []) + [f"✓ Research Brief Agent created brief ({mode_label})"],
    }


async def supervisor_node(state: ResearchGraphState) -> dict:
    brief = state.get("research_brief", "")
    offline = state.get("offline", False)
    
    if not brief:
        return {"tasks": [], "progress_logs": state.get("progress_logs", []) + ["⚠ Empty research brief"]}

    print("\n[STAGE 2/3] Supervisor Agent analyzing brief and delegating missions...")

    if offline:
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
        print("  ✓ Supervisor decomposed into 3 balanced missions (offline)")
        return {
            "tasks": tasks,
            "final_summary": None,
            "progress_logs": state.get("progress_logs", []) + ["✓ Supervisor Agent decomposed brief into 3 balanced missions (offline)"],
        }

    try:
        sup_state = run_supervisor(brief)
        tasks_data = [t if isinstance(t, dict) else t.model_dump() for t in sup_state.tasks]
        print(f"  ✓ Supervisor decomposed into {len(tasks_data)} balanced missions (live LLM)")
        return {
            "tasks": tasks_data,
            "final_summary": sup_state.final_summary,
            "progress_logs": state.get("progress_logs", []) + [f"✓ Supervisor Agent decomposed brief into {len(tasks_data)} balanced missions (live)"],
        }
    except Exception as exc:
        print(f"  ✗ Supervisor error: {exc}")
        return {
            "tasks": [],
            "progress_logs": state.get("progress_logs", []) + [f"✗ Supervisor Agent error: {exc}"],
        }


async def research_execution_node(state: ResearchGraphState) -> dict:
    tasks = state.get("tasks", [])
    brief = state.get("research_brief", "")
    query = state.get("query", "")
    offline = state.get("offline", False)

    if not tasks:
        return {"tasks": tasks, "progress_logs": state.get("progress_logs", []) + ["⚠ No tasks to execute"]}

    print(f"\n[STAGE 3/3] Research Agents executing {len(tasks)} assigned missions...")
    executed_tasks = await run_research_agents(tasks, brief, query, offline=offline)
    print("  ✓ All research missions successfully executed!")

    return {
        "tasks": executed_tasks,
        "progress_logs": state.get("progress_logs", []) + [f"✓ Executed {len(executed_tasks)} research missions across Research Agents"],
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
) -> dict:
    provider = os.getenv("LLM_PROVIDER", "groq").upper()
    model = os.getenv("LLM_MODEL", "qwen/qwen3.8-27b")
    mode_label = "OFFLINE DETERMINISTIC BLUEPRINT" if offline else f"LIVE API [{provider} | Model: {model}]"

    print("\n" + "=" * 80)
    print(">> EXECUTING MULTI-AGENT RESEARCH PIPELINE (LangGraph)")
    print(f"MODE   : {mode_label}")
    print(f"QUERY  : {query}")
    print(f"CONTEXT: {context or 'None'}")
    print("=" * 80)

    initial_state = {
        "query": query,
        "clarified_request": query,
        "context": context or None,
        "offline": offline,
        "progress_logs": [],
    }

    final_state = await pipeline.ainvoke(initial_state)

    # 1. Print Public Research Brief
    print("\n" + "=" * 80)
    print(">> 1. STRATEGIC RESEARCH BRIEF (Passed to Supervisor Agent)")
    print("=" * 80)
    print(final_state.get("research_brief", "No brief generated."))

    # 2. Print Supervisor Delegation Plan
    print("\n" + "=" * 80)
    print(">> 2. SUPERVISOR DELEGATION PLAN (Workload Distribution)")
    print("=" * 80)
    tasks = final_state.get("tasks", [])
    agent_counts = {}
    for t in tasks:
        agent = t.get("assigned_agent", "Unassigned")
        agent_counts[agent] = agent_counts.get(agent, 0) + 1

    print(f"\nTotal Tasks: {len(tasks)}")
    print("Agent Load Distribution:")
    for agent, count in sorted(agent_counts.items()):
        print(f"  * {agent}: {count} missions")

    print("\nDelegated Missions:")
    for i, t in enumerate(tasks, 1):
        task_id = t.get("task_id", f"task_{i}")
        agent = t.get("assigned_agent", "Unassigned")
        status = t.get("status", "pending").upper()
        print(f"\n[{task_id}] -> ASSIGNED TO: {agent} | STATUS: {status}")
        print(f"Mission:\n{t.get('task_description')}")

    # 3. Print Detailed Research Findings with Tool Logs
    print("\n" + "=" * 80)
    print(">> 3. DETAILED RESEARCH FINDINGS & EMPIRICAL SYNTHESIS (Parallel Agents)")
    print("=" * 80)
    findings_blocks = []
    for t in tasks:
        task_id = t.get("task_id", "task")
        agent = t.get("assigned_agent", "ResearchAgent")
        desc = t.get("task_description", "")
        status = t.get("status", "pending").upper()
        result_body = t.get("result", "No findings reported.")
        findings_blocks.append(f"### Mission [{task_id.upper()}] ({agent})\n\n**Goal**: {desc}\n\n{result_body}")

        tool_calls = t.get("tool_calls", [])
        tool_outputs = t.get("tool_outputs", [])

        print(f"\n{'─' * 80}")
        print(f"[{task_id.upper()}] — {agent} (STATUS: {status})")
        print(f"Mission: {desc}")
        
        if tool_calls:
            print(f"\n[TOOL CALL LOGS]:")
            for tc in tool_calls:
                print(f"  • Tool Name: {tc.get('tool_name')}")
                print(f"    Arguments: {json.dumps(tc.get('arguments', {}))}")
        if tool_outputs:
            print(f"\n[TOOL OUTPUT EVIDENCE]:")
            for to in tool_outputs:
                print(f"  • Query: \"{to.get('query')}\" -> {to.get('results_count', 0)} sources retrieved")
                for r_idx, res in enumerate(to.get("results", [])[:3], 1):
                    print(f"    [{r_idx}] {res.get('title')}")
                    print(f"        Origin : {res.get('origin_type', 'Web Source')}")
                    print(f"        DOI/URL: {res.get('url')}")
                    if res.get("snippet"):
                        print(f"        Snippet: {res.get('snippet')[:110]}...")

        print(f"\n[SYNTHESIZED REPORT]:")
        print(f"{'─' * 80}")
        print(result_body)

    if final_state.get("brief_self_evaluation"):
        print("\n" + "=" * 80)
        print(">> 4. INTERNAL DEVELOPER DIAGNOSTIC (Private Self-Evaluation)")
        print("=" * 80)
        print("Self-evaluation diagnostic recorded.")

    # Save outputs if requested
    if output_file:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if str(out_path).endswith(".json"):
            out_data = {
                "mode": mode_label,
                "query": query,
                "context": context,
                "research_brief": final_state.get("research_brief"),
                "tasks": final_state.get("tasks"),
                "agent_distribution": agent_counts,
                "internal_self_evaluation": final_state.get("brief_self_evaluation"),
            }
            out_path.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
        else:
            text_content = (
                f"# MULTI-AGENT RESEARCH DOSSIER\n"
                f"Mode: {mode_label}\n"
                f"Query: {query}\n"
                f"Context: {context or 'None'}\n"
                f"{'=' * 80}\n\n"
                f"## 1. STRATEGIC RESEARCH BRIEF\n\n"
                f"{final_state.get('research_brief', 'None')}\n\n"
                f"{'=' * 80}\n\n"
                f"## 2. SUPERVISOR DELEGATION PLAN\n\n"
                f"Total Tasks: {len(tasks)}\n"
                f"Agent Load Distribution: {json.dumps(agent_counts)}\n\n"
                + "\n\n".join([f"- [{t.get('task_id')}] ({t.get('assigned_agent')}): {t.get('task_description')}" for t in tasks])
                + f"\n\n{'=' * 80}\n\n"
                f"## 3. DETAILED RESEARCH FINDINGS & EMPIRICAL SYNTHESIS\n\n"
                + "\n\n---\n\n".join(findings_blocks)
                + f"\n\n{'=' * 80}\n\n"
                f"## 4. INTERNAL DEVELOPER DIAGNOSTIC (Self-Evaluation)\n\n"
                + f"{final_state.get('brief_self_evaluation', 'None')}"
            )
            out_path.write_text(text_content.strip() + "\n", encoding="utf-8")
        print(f"\n[Saved Output]: {out_path}")

    print("\n" + "=" * 80 + "\n")
    return final_state


def main():
    parser = argparse.ArgumentParser(description="Run the full ARGUS Multi-Agent Research Pipeline.")
    parser.add_argument(
        "query",
        nargs="?",
        default="What are the major causes of urban air pollution?",
        help="Research query / topic",
    )
    parser.add_argument("--context", default="A city public-health team needs a neutral overview.", help="Optional context")
    parser.add_argument("--offline", action="store_true", help="Run in offline mode using deterministic domain blueprints")
    parser.add_argument("--output", "-o", default=None, help="Path to save output (.txt or .json)")
    parser.add_argument("--audit-citations", action="store_true", help="Run LLM-as-a-Judge citation authenticity & hallucination audit")
    args = parser.parse_args()

    state = asyncio.run(run_pipeline(args.query, args.context, args.offline, args.output))
    
    if args.audit_citations:
        try:
            from tests.test_citation_judge import LLMCitationJudge, print_judge_report
        except ImportError:
            from test.test_citation_judge import LLMCitationJudge, print_judge_report
        all_text = ""
        for t in state.get("tasks", []):
            all_text += f"\n{t.get('result', '')}"
        judge = LLMCitationJudge()
        report = asyncio.run(judge.judge_citations(all_text))
        print_judge_report(report)


if __name__ == "__main__":
    main()
