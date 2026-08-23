# Research Brief Agent

## Responsibility

The Research Brief Agent converts a clarified user request into a Supervisor-ready research mission. It is a planning boundary, not a research executor: it never searches, synthesizes findings, manages workers, or writes the final report.

## Input

`ResearchBriefInput` accepts `request_id`, `clarified_request`, optional original query/context, constraints, and clarification notes. The graph node reads these from shared `State` fields populated by the Clarify Agent.

## Output and handoff

The result contains a plain-language Markdown research brief and a prose self-evaluation. The brief naturally covers the research question, objective, scope, questions, evidence requirements, suggested delegable tasks, expected deliverable, assumptions, and any clarification needed, but it is not emitted as JSON.

`ResearchBriefNode.execute()` writes the plain-text brief to `research_brief` and `supervisor_input`; the latter is the explicit Supervisor handoff. The Supervisor decides worker count, assignment, tools, execution order, and report production.

## Self-evaluation

The agent must return scores from 0–10 for question clarity, scope, completeness, decomposition, task quality, evidence requirements, relevance, downstream potential, and ambiguity handling. It also records specific reasoning, strengths, weaknesses, and improvements. The deterministic fallback evaluates its own generated structure rather than pretending research occurred.

## Provider behavior

Configured providers are asked for readable Markdown prose. If no provider is configured, an offline deterministic planner creates a conservative plain-language brief, marks missing framing as clarification needed, and never invents findings or sources.

## Evaluation corpus

`eval/datasets/research_brief_cases.json` holds seven cases: simple, comparative, multi-dimensional, ambiguous, conflicting-evidence, insufficient-information, and complex. Run `python -m eval.evaluate_research_brief --offline` to save an inspectable report with every input, brief, self-evaluation, score, weaknesses, and improvements.
