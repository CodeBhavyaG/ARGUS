import asyncio
import logging
import sys
import unittest
import warnings
from pathlib import Path

# Suppress verbose asyncio slow task warnings
logging.getLogger("asyncio").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test.test_citation_judge import LLMCitationJudge, CitationVerifier, print_judge_report

if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        target_path = Path(sys.argv[1])
        if target_path.exists():
            content = target_path.read_text(encoding="utf-8")
        else:
            content = sys.argv[1]
        judge = LLMCitationJudge()
        rep = asyncio.run(judge.judge_citations(content))
        print_judge_report(rep)
    else:
        unittest.main(module="test.test_citation_judge", argv=sys.argv)
