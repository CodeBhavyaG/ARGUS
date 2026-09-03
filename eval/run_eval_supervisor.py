"""
Runner script to evaluate the Supervisor Agent on the benchmark research briefs
extracted from research_brief_supervisor_brief_evaluation.pdf.
"""

import os
import sys
import json
import time
from pathlib import Path

# Ensure root is on sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from eval.eval_cases import EVALUATION_CASES
from eval.evaluator import SupervisorEvaluator
from agent.Superviser import run_supervisor


def run_benchmark_evaluation(save_report: bool = True):
    """
    Run evaluation across all test cases, compute scores and reasons, and save reports.
    """
    evaluator = SupervisorEvaluator()
    results = []
    
    print("=" * 80)
    print("STARTING SUPERVISOR AGENT BENCHMARK EVALUATION (7 CASES)")
    print("=" * 80)

    for i, case in enumerate(EVALUATION_CASES, start=1):
        case_id = case["id"]
        category = case["category"]
        query = case["research_query"]
        brief = case["research_brief"]
        
        print(f"\n[{i}/7] Evaluating Case '{case_id}' (Category: {category})")
        print(f"Query: \"{query}\"")
        print("-" * 60)
        
        start_time = time.time()
        try:
            supervisor_output = run_supervisor(brief)
            latency = round(time.time() - start_time, 2)
            out_dict = supervisor_output.model_dump()
        except Exception as e:
            print(f"Error executing supervisor on {case_id}: {e}")
            continue

        eval_result = evaluator.evaluate(
            brief=brief,
            output=out_dict,
            case_id=case_id,
            category=category,
        )
        
        eval_result["latency_seconds"] = latency
        eval_result["input_query"] = query
        eval_result["supervisor_output"] = out_dict
        results.append(eval_result)

        print(f"  * Overall Score: {eval_result['overall_score']}/10")
        print(f"  * Tasks Generated: {eval_result['metrics']['task_count']}")
        print(f"  * Agent Distribution: {eval_result['metrics']['agent_distribution']} (Load Delta: {eval_result['metrics']['load_delta']})")
        print(f"  * Latency: {latency}s")
        print(f"  * Reason: {eval_result['reason']}")

    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)

    avg_score = round(sum(r["overall_score"] for r in results) / len(results), 2) if results else 0.0
    print(f"Total Cases Evaluated: {len(results)}/7")
    print(f"Mean Overall Score:    {avg_score}/10.0")
    print("=" * 80)

    # Save JSON results
    output_json_path = project_root / "eval" / "evaluation_results.json"
    output_json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Detailed results saved to: {output_json_path}")

    # Generate Markdown Report
    if save_report:
        report_md_path = project_root / "eval" / "EVALUATION_REPORT.md"
        report_content = generate_markdown_report(results, avg_score)
        report_md_path.write_text(report_content, encoding="utf-8")
        print(f"Markdown report generated at: {report_md_path}")

    return results


def generate_markdown_report(results: list, avg_score: float) -> str:
    """Generate structured markdown evaluation report."""
    md = []
    md.append("# Supervisor Agent — Evaluation Report\n")
    md.append(f"**Benchmark Dataset:** `research_brief_supervisor_brief_evaluation.pdf` (7 cases)")
    md.append(f"**Target System:** `agent/Superviser.py`")
    md.append(f"**Evaluated Model:** `qwen/qwen3.6-27b` via Groq")
    md.append(f"**Average Benchmark Score:** **{avg_score}/10.0**\n")
    md.append("---\n")

    md.append("## 1. Executive Summary Table\n")
    md.append("| Case ID | Category | Query | Tasks | Agent Distribution | Score / 10 | Status |")
    md.append("|---|---|---|---|---|---|---|")
    for r in results:
        dist = ", ".join([f"{k.replace('ResearchAgent_', 'A')}:{v}" for k, v in r["metrics"]["agent_distribution"].items()])
        status = "PASSED (Excellent)" if r["overall_score"] >= 9.0 else "PASSED" if r["overall_score"] >= 8.0 else "NEEDS IMPROVEMENT"
        md.append(f"| `{r['case_id']}` | **{r['category']}** | {r['input_query'][:38]}... | {r['metrics']['task_count']} | `{dist}` | **{r['overall_score']}/10** | {status} |")
    md.append("\n---\n")

    md.append("## 2. Detailed Case-by-Case Evaluation\n")
    for i, r in enumerate(results, start=1):
        md.append(f"### Case {i}: `{r['case_id']}` — Category: {r['category']}")
        md.append(f"**Research Query:** {r['input_query']}")
        md.append(f"**Rating:** **{r['overall_score']} / 10.0**")
        md.append(f"**Brief Reason:** {r['reason']}\n")

        md.append("#### Dimensional Score Breakdown")
        md.append(f"- **Strict Load Balancing (2.5 max):** {r['dimensions']['load_balancing']} / 2.5")
        md.append(f"- **Context Clustering & Decomposition (2.5 max):** {r['dimensions']['context_clustering']} / 2.5")
        md.append(f"- **Actionability & Instruction Clarity (2.0 max):** {r['dimensions']['actionability']} / 2.0")
        md.append(f"- **Schema & Operational Constraints (1.5 max):** {r['dimensions']['schema_constraints']} / 1.5")
        md.append(f"- **Scope & Edge Case Coverage (1.5 max):** {r['dimensions']['scope_coverage']} / 1.5\n")

        md.append("#### Key Metrics")
        md.append(f"- **Task Count:** {r['metrics']['task_count']}")
        md.append(f"- **Agent Distribution:** `ResearchAgent_1`: {r['metrics']['agent_distribution'].get('ResearchAgent_1', 0)}, `ResearchAgent_2`: {r['metrics']['agent_distribution'].get('ResearchAgent_2', 0)}, `ResearchAgent_3`: {r['metrics']['agent_distribution'].get('ResearchAgent_3', 0)}")
        md.append(f"- **Load Delta (Max - Min):** {r['metrics']['load_delta']} (Constraint: <= 1)")
        md.append(f"- **Average Words per Task:** {r['metrics']['avg_words_per_task']}")
        md.append(f"- **Execution Latency:** {r.get('latency_seconds', 'N/A')}s\n")

        md.append("#### Generated Tasks & Delegations")
        for t_idx, task in enumerate(r["supervisor_output"].get("tasks", []), start=1):
            md.append(f"{t_idx}. **[{task.get('assigned_agent')}]** `{task.get('status')}`")
            md.append(f"   - *Instructions:* {task.get('task_description')}")
        md.append("")

        if r["strengths"]:
            md.append("**Strengths:**")
            for s in r["strengths"]:
                md.append(f"- {s}")
            md.append("")

        if r["weaknesses"]:
            md.append("**Weaknesses:**")
            for w in r["weaknesses"]:
                md.append(f"- {w}")
            md.append("")

        md.append("---\n")

    return "\n".join(md)


if __name__ == "__main__":
    run_benchmark_evaluation()
