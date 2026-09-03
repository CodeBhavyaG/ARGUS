# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

### Setup & Installation

```bash
# Install the package in editable mode
python -m pip install -e .

# Install development dependencies
python -m pip install -e ".[dev]"
```

### Running the Pipeline

```bash
# Run the main CLI pipeline (live Groq API)
python -m sih_hackathon.main "Your research query here"

# Run in offline mode (deterministic blueprints, no API key needed)
python -m sih_hackathon.main "Your research query here" --offline

# Run with custom context
python -m sih_hackathon.main "Your query" --context "Additional context"
```

### Testing

```bash
# Run all tests
python -m pytest -q

# Run a specific test file
python -m pytest tests/test_research_brief.py -q
python -m pytest tests/test_supervisor.py -q

# Run tests with verbose output
python -m pytest -v
```

### Evaluation

```bash
# Run offline evaluation
python -m eval.evaluate_research_brief --offline

# Run the research brief test script
python -m scripts.run_research_brief_test
```

### Development

```bash
# Lint the codebase
python -m flake8

# Check code formatting
python -m black .

# Run type checking if mypy is installed
python -m mypy src/
```

---

## High-Level Architecture

This is a **multi-agent LangGraph research pipeline** with the following structure:

```
Clarify Agent → Research Brief Agent → Supervisor Agent → Researchers → Report Agent
```

### Core Components

1. **`main.py`** — CLI entrypoint that orchestrates the LangGraph pipeline. Accepts a research query and optional context, then runs the pipeline offline or live via Groq API.

2. **`src/sih_hackathon/state.py`** — Defines the graph state types (`ResearchGraphState`, `SupervisorState`) and a Pydantic `State` model for validation. The research graph state tracks: query, research brief, tasks, progress logs, and offline flag.

3. **`src/sih_hackathon/research_brief/`** — Research Brief Agent sub-package:
   - `models.py` — `ResearchBriefInput` / `ResearchBriefResult` data models
   - `config.py` — `ResearchBriefConfig` configuration
   - `service.py` — `ResearchBriefService` that creates briefs via LLM
   - `__init__.py` — Package exports

4. **`agent/ResearchBrief.py`** — High-level runner for the Research Brief Agent. Loads `.env` config, delegates to `ResearchBriefService`. Exports `run_research_brief()`.

5. **`agent/Superviser.py`** — Supervisor Agent creator. Uses LangChain's `create_agent` with a structured `SupervisorState` response format. Loads system prompt from `prompt/Superviser.md`. Exports `run_supervisor()`.

6. **`prompt/ResearchBrief.md`** — System prompt for the Research Brief Agent, defining its role, scope, delegation suggestions, edge cases, and expected deliverable.

7. **`prompt/Superviser.md`** — System prompt for the Supervisor Agent, defining task delegation across 5 research domains (emission sources, meteorology, public health, regulatory policies, edge cases/anomalies).

8. **`state.py` (root)** — Alternative Pydantic state model with `extra="allow"` for backward compatibility.

9. **`eval/`** — Evaluation tooling including evaluation cases, evaluators, and an offline report runner.

10. **`tests/`** — Project tests: `test_research_brief.py` and `test_supervisor.py`.

### Key Data Flow

```
Query → research_brief_node → research_brief → supervisor_node → tasks/final_summary → END
```

The pipeline compiles into a LangGraph with two nodes (`research_brief`, `supervisor`) and three edges (`START → research_brief → supervisor → END`).

### Offline vs Live Mode

- **Offline** (`--offline` flag): Uses deterministic domain blueprints built into the supervisor node. No API keys required. Generates 3 fixed research missions.
- **Live** (default): Calls Groq API through LangChain. The supervisor dynamically decomposes the brief into tasks assigned to research agents. Task count and agent distribution vary by query.

### Architecture Conventions

- **State flows unidirectionally** through the LangGraph; any node can update `progress_logs` by appending to the list.
- **Pydantic models** with `extra="allow"` are used for state validation and backward compatibility.
- **System prompts** live in `prompt/` and are loaded at runtime via `get_system_prompt()`.
- **`.env`** at the repository root holds `GROQ_API_KEY` and `LLM_PROVIDER`/`LLM_MODEL` — never commit the real `.env`.
- **Copy `configs/.env.example` → `.env`** and fill in real API keys before running in live mode.