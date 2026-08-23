import asyncio

from .research_brief.models import ResearchBriefInput
from .research_brief.service import ResearchBriefService


async def demo_research_brief():
    result = await ResearchBriefService().create_brief(ResearchBriefInput(
        request_id="demo-1",
        clarified_request="Compare electric and hybrid vehicles on total cost, environmental impact, maintenance, and long-term adoption.",
    ))
    print("Research brief:")
    print(result.brief if result.brief else result.error)
    print("Self-evaluation:")
    print(result.self_evaluation or "Unavailable")


def main():
    print("Starting Research Brief Agent demo...")
    asyncio.run(demo_research_brief())


if __name__ == "__main__":
    main()
