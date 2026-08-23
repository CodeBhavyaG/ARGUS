"""Export Research Brief evaluation results into a single consolidated plain-text (.txt) file for the Supervisor Agent."""
import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export research brief results to a single plain-text file for the Supervisor.")
    parser.add_argument("input", type=Path, help="Path to evaluation JSON report file")
    parser.add_argument("--output", "-o", type=Path, default=Path("eval/outputs/supervisor_research_briefs.txt"), help="Path to save the consolidated text file")
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)

    consolidated = [
        f"# RESEARCH BRIEF AGENT — SUPERVISOR HANDOFF DOSSIER\n"
        f"Generated: {report['metadata'].get('created_at', 'N/A')}\n"
        f"Mode: {report['metadata'].get('mode', 'N/A')}\n"
        f"Model: {report['metadata'].get('model', 'N/A')}\n"
        f"Total Cases: {report['metadata'].get('case_count', len(report['results']))}\n"
        f"{'=' * 80}"
    ]

    for index, row in enumerate(report["results"], 1):
        brief = row.get("generated_research_brief") or ""
        if not brief:
            continue
        case_id = row["id"]
        content = brief
        if row.get("self_evaluation") and "The self-evaluation is included" not in row["self_evaluation"]:
            content += f"\n\n{row['self_evaluation']}"

        block = (
            f"\n\n{'=' * 80}\n"
            f"CASE {index}: {case_id} — CATEGORY: {row['category'].upper()}\n"
            f"QUERY: {row['input']['research_query']}\n"
            f"CONTEXT: {row['input']['context'] or 'None'}\n"
            f"{'=' * 80}\n\n"
            f"{content.strip()}"
        )
        consolidated.append(block)

    args.output.write_text("\n".join(consolidated) + "\n", encoding="utf-8")
    print(f"[Consolidated Supervisor File Saved]: {args.output}")


if __name__ == "__main__":
    main()
