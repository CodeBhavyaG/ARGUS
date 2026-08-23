"""Evaluate Research Brief Agent outputs against a multi-category planning corpus.

Use ``python -m eval.evaluate_research_brief --offline`` for deterministic fallback
testing, or omit ``--offline`` to use the configured provider.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sih_hackathon.research_brief.config import ResearchBriefConfig
from sih_hackathon.research_brief.models import ResearchBriefInput
from sih_hackathon.research_brief.service import ResearchBriefService
DATASET = ROOT / "eval" / "datasets" / "research_brief_cases.json"
OUTPUT_DIR = ROOT / "eval" / "outputs"


def load_dataset() -> list[dict[str, Any]]:
    return json.loads(DATASET.read_text(encoding="utf-8"))


def coverage(expected: list[str], actual: list[str]) -> float:
    text = " ".join(actual).lower()
    if not expected:
        return 10.0
    return round(10 * sum(any(word.strip("?,.:;\"'") in text for word in item.lower().split() if len(word.strip("?,.:;\"'")) > 4) for item in expected) / len(expected), 1)


def score_case(case: dict[str, Any], result) -> dict[str, Any]:
    if not result.success or not result.brief:
        return {"overall_score": 0.0, "dimensions": {}, "reasoning": result.error or "No brief generated.", "weaknesses": ["Generation failed."], "improvements": ["Fix runtime failure."]}
    output = result.brief.lower()
    areas = coverage(case["expected_research_areas"], [output])
    questions = coverage(case["expected_sub_questions"], [output])
    tasks = 10.0 if "delegation suggestions" in output else 2.0
    evidence = 10.0 if "evidence" in output else 2.0
    ambiguity = 10.0 if case["category"] not in {"ambiguous", "insufficient_information"} or any(k in output for k in ("clarification needed", "assumptions & clarification", "clarification")) else 2.0
    self_eval_text = ((result.self_evaluation or "") + " " + output).lower()
    self_eval_quality = 9.0 if any(k in self_eval_text for k in ("overall score", "score:", "score :", "score: ", "self-evaluation", "self‑evaluation", "strengths:")) else 3.0
    dimensions = {"area_coverage": areas, "question_decomposition": questions, "task_usefulness": tasks, "evidence_requirements": evidence, "ambiguity_handling": ambiguity, "self_evaluation_quality": self_eval_quality}
    overall = round(sum(dimensions.values()) / len(dimensions), 1)
    weaknesses = []
    if areas < 6: weaknesses.append("Expected research areas have limited lexical coverage in the generated brief.")
    if ambiguity < 6: weaknesses.append("The case requires clarification, but the brief did not preserve it clearly.")
    return {"overall_score": overall, "dimensions": dimensions, "reasoning": "Plain-language output was checked for expected research coverage, task and evidence sections, ambiguity handling, and a self-evaluation.", "weaknesses": weaknesses, "improvements": ["Add more topic-specific detail where lexical coverage is low."]}


async def evaluate(offline: bool = False, case_ids: set[str] | None = None) -> dict[str, Any]:
    config = ResearchBriefConfig(llm_provider="local", llm_api_key=None) if offline else ResearchBriefConfig()
    service, rows = ResearchBriefService(config=config), []
    for case in load_dataset():
        if case_ids and case["id"] not in case_ids:
            continue
        result = await service.create_brief(ResearchBriefInput(request_id=case["id"], clarified_request=case["research_query"], context=case["context"]))
        rows.append({"id": case["id"], "category": case["category"], "input": {"research_query": case["research_query"], "context": case["context"]}, "reference_brief": case["reference_brief"], "generated_research_brief": result.brief or None, "self_evaluation": result.self_evaluation or None, "score": score_case(case, result), "runtime": {"success": result.success, "error": result.error}})
    average = round(sum(row["score"]["overall_score"] for row in rows) / len(rows), 2)
    return {"metadata": {"created_at": datetime.now(timezone.utc).isoformat(), "mode": "offline fallback" if offline else "live configured provider", "model": config.llm_model, "case_count": len(rows)}, "results": rows, "aggregate": {"average_overall_score": average, "lowest_cases": [r["id"] for r in rows if r["score"]["overall_score"] == min(x["score"]["overall_score"] for x in rows)]}}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--offline", action="store_true"); parser.add_argument("--ids", nargs="*", help="Optional dataset IDs to run")
    args = parser.parse_args()
    report = asyncio.run(evaluate(args.offline, set(args.ids) if args.ids else None))
    OUTPUT_DIR.mkdir(exist_ok=True)
    suffix = "_" + "_".join(args.ids) if args.ids else ""
    output = OUTPUT_DIR / (f"research_brief_evaluation_offline{suffix}.json" if args.offline else f"research_brief_evaluation{suffix}.json")
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Export one single consolidated plain-text handoff file for the Supervisor
    consolidated_blocks = [
        f"# RESEARCH BRIEF AGENT — SUPERVISOR HANDOFF DOSSIER\n"
        f"Generated: {report['metadata']['created_at']}\n"
        f"Mode: {report['metadata']['mode']}\n"
        f"Model: {report['metadata']['model']}\n"
        f"Total Cases: {report['metadata']['case_count']}\n"
        f"{'=' * 80}"
    ]
    for index, row in enumerate(report["results"], 1):
        if row.get("generated_research_brief"):
            block = (
                f"\n\n{'=' * 80}\n"
                f"CASE {index}: {row['id']} — CATEGORY: {row['category'].upper()}\n"
                f"QUERY: {row['input']['research_query']}\n"
                f"CONTEXT: {row['input']['context'] or 'None'}\n"
                f"{'=' * 80}\n\n"
                f"{row['generated_research_brief']}"
            )
            if row.get("self_evaluation") and "The self-evaluation is included" not in row["self_evaluation"]:
                block += f"\n\n{row['self_evaluation']}"
            consolidated_blocks.append(block)

    single_txt_path = OUTPUT_DIR / (f"supervisor_research_briefs_offline{suffix}.txt" if args.offline else f"supervisor_research_briefs{suffix}.txt")
    single_txt_path.write_text("\n".join(consolidated_blocks) + "\n", encoding="utf-8")

    print(json.dumps({"output": str(output), "supervisor_text_output": str(single_txt_path), "aggregate": report["aggregate"]}, indent=2))


if __name__ == "__main__": main()
