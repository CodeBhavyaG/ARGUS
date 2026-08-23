"""Create and print one Supervisor-ready research brief."""
import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sih_hackathon.research_brief.models import ResearchBriefInput
from sih_hackathon.research_brief.service import ResearchBriefService


async def run(query: str, context: str, output_file: str | None = None) -> None:
    result = await ResearchBriefService().create_brief(ResearchBriefInput(request_id="manual-demo", clarified_request=query, context=context or None))
    if not result.success:
        print(f"Unable to create research brief: {result.error}")
        return
    full_output = result.brief
    if result.self_evaluation and "The self-evaluation is included" not in result.self_evaluation:
        full_output += f"\n\n{result.self_evaluation}"
    print(full_output)
    if output_file:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(full_output.strip() + "\n", encoding="utf-8")
        print(f"\n[Supervisor Handoff Saved]: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a research brief for the Supervisor.")
    parser.add_argument("query", nargs="?", default="What are the major causes of urban air pollution?")
    parser.add_argument("--context", default="")
    parser.add_argument("--output", "-o", default="eval/outputs/supervisor_research_brief.txt", help="Path to save supervisor plain-text handoff")
    args = parser.parse_args()
    asyncio.run(run(args.query, args.context, args.output))
