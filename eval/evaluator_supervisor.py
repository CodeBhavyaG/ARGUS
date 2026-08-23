"""
Comprehensive evaluation engine for Supervisor Agent in agent/Superviser.py.

Evaluates task decomposition, load balancing, agent assignment, instruction actionability,
schema conformance, and scope/edge case coverage on a scale of 0 to 10 with detailed reasoning.
"""

from typing import Any, Dict, List
import re
from state import SupervisorState


VALID_AGENTS = {"ResearchAgent_1", "ResearchAgent_2", "ResearchAgent_3"}


class SupervisorEvaluator:
    """
    Evaluator for Supervisor Agent outputs against predefined quality benchmarks.
    """

    def __init__(self):
        pass

    def evaluate(
        self,
        brief: str,
        output: SupervisorState | Dict[str, Any],
        case_id: str = "custom_case",
        category: str = "GENERAL",
    ) -> Dict[str, Any]:
        """
        Evaluate a single Supervisor output against the evaluation rubric.
        Returns overall score out of 10, dimensional breakdown, metrics, strengths, weaknesses, and a brief reason.
        """
        if isinstance(output, SupervisorState):
            out_dict = output.model_dump()
        elif isinstance(output, dict):
            out_dict = output
        else:
            raise ValueError(f"Unsupported output type: {type(output)}")

        tasks: List[Dict[str, Any]] = out_dict.get("tasks", [])
        research_brief_str: str = out_dict.get("research_brief", "")
        final_summary = out_dict.get("final_summary")

        strengths: List[str] = []
        weaknesses: List[str] = []
        improvements: List[str] = []

        # -------------------------------------------------------------
        # 1. Dimension: Strict Load Balancing (Weight: 2.5 pts)
        # -------------------------------------------------------------
        score_lb = 0.0
        agent_counts = {agent: 0 for agent in VALID_AGENTS}
        invalid_agents = []

        for t in tasks:
            agent = t.get("assigned_agent", "")
            if agent in VALID_AGENTS:
                agent_counts[agent] += 1
            else:
                invalid_agents.append(agent)

        num_tasks = len(tasks)

        # 1a. Valid agent names (1.0 pt)
        if num_tasks > 0 and len(invalid_agents) == 0:
            score_lb += 1.0
            strengths.append(f"All {num_tasks} tasks assigned to valid subordinate agents.")
        elif len(invalid_agents) > 0:
            score_lb += max(0.0, 1.0 - 0.75 * len(invalid_agents))
            weaknesses.append(f"Found invalid assigned agents: {invalid_agents}")

        # 1b. Agent utilization (0.75 pt)
        active_agents = [a for a, c in agent_counts.items() if c > 0]
        if num_tasks >= 3:
            if len(active_agents) == 3 and len(invalid_agents) == 0:
                score_lb += 0.75
                strengths.append("Full agent utilization: all 3 research agents actively assigned tasks.")
            else:
                unused = [a for a, c in agent_counts.items() if c == 0]
                weaknesses.append(f"Under-utilized agent pool: {unused} remained idle despite {num_tasks} tasks.")
                score_lb += 0.2 * len(active_agents)
        elif num_tasks > 0:
            if len(active_agents) == num_tasks and len(invalid_agents) == 0:
                score_lb += 0.75
                strengths.append(f"Optimal 1-to-1 agent allocation for {num_tasks} subtopics.")
            elif len(invalid_agents) == 0:
                score_lb += 0.4

        # 1c. Load delta / anti-overload guardrail (0.75 pt)
        if num_tasks > 0 and len(invalid_agents) == 0:
            counts_list = list(agent_counts.values()) if num_tasks >= 3 else [agent_counts[a] for a in active_agents]
            max_c = max(counts_list) if counts_list else 0
            min_c = min(counts_list) if counts_list else 0
            load_delta = max_c - min_c

            if load_delta <= 1:
                score_lb += 0.75
                strengths.append(f"Strict load balance achieved (max task load delta = {load_delta} <= 1).")
            else:
                weaknesses.append(f"Load imbalance detected (max task delta = {load_delta} > 1). Distribution: {agent_counts}")
                score_lb += max(0.0, 0.75 - 0.25 * (load_delta - 1))
        else:
            load_delta = max(agent_counts.values()) if agent_counts else 0

        # -------------------------------------------------------------
        # 2. Dimension: Context-Aware Clustering & Non-Overlapping Decomposition (Weight: 2.5 pts)
        # -------------------------------------------------------------
        score_decomp = 0.0

        # 2a. Task count adequacy (1.0 pt)
        if 3 <= num_tasks <= 6:
            score_decomp += 1.0
            strengths.append(f"Decomposed brief into {num_tasks} well-sized subtopics.")
        elif num_tasks in (1, 2, 7):
            score_decomp += 0.6
            weaknesses.append(f"Task count ({num_tasks}) is marginally suboptimal for comprehensive multi-agent research.")
        else:
            score_decomp += 0.2
            weaknesses.append(f"Task count ({num_tasks}) is either empty or excessively fragmented.")

        # 2b. Non-overlapping & distinct descriptions (1.0 pt)
        task_descriptions = [t.get("task_description", "").strip() for t in tasks]
        unique_tasks = set(task_descriptions)
        if len(unique_tasks) == num_tasks and num_tasks > 0:
            # Check pairwise token overlap
            has_high_redundancy = False
            for i in range(len(task_descriptions)):
                for j in range(i + 1, len(task_descriptions)):
                    words_i = set(task_descriptions[i].lower().split())
                    words_j = set(task_descriptions[j].lower().split())
                    if words_i and words_j:
                        jaccard = len(words_i & words_j) / len(words_i | words_j)
                        if jaccard > 0.65:
                            has_high_redundancy = True
            if not has_high_redundancy:
                score_decomp += 1.0
                strengths.append("High subtopic distinctiveness: zero redundant or overlapping research objectives.")
            else:
                score_decomp += 0.6
                weaknesses.append("Noticeable semantic overlap detected between some delegated subtopics.")
        else:
            score_decomp += 0.3
            weaknesses.append("Duplicate task descriptions detected.")

        # 2c. Semantic grouping / Context coherence (0.5 pt)
        score_decomp += 0.5

        # -------------------------------------------------------------
        # 3. Dimension: Actionability & Instructions Clarity (Weight: 2.0 pts)
        # -------------------------------------------------------------
        score_act = 0.0
        word_counts = [len(desc.split()) for desc in task_descriptions]
        avg_words = sum(word_counts) / len(word_counts) if word_counts else 0

        # 3a. Instruction depth & specificity (1.0 pt)
        if avg_words >= 35:
            score_act += 1.0
            strengths.append(f"Exemplary instruction depth (average {avg_words:.1f} words/task with domain specifics).")
        elif avg_words >= 20:
            score_act += 0.75
            strengths.append(f"Good instruction clarity (average {avg_words:.1f} words/task).")
        elif avg_words > 0:
            score_act += 0.4
            weaknesses.append(f"Instructions are overly brief (average {avg_words:.1f} words/task).")
        else:
            weaknesses.append("Task descriptions are empty.")

        # 3b. Non-execution rule / explicit directives (0.5 pt)
        # Verify tasks contain directives ("investigate", "examine", "analyze", "evaluate", "synthesize", etc.)
        action_verbs = {"investigate", "examine", "analyze", "evaluate", "synthesize", "assess", "review", "map", "compare", "document", "quantify", "determine"}
        actionable_count = 0
        for desc in task_descriptions:
            desc_words = set(re.findall(r'\b\w+\b', desc.lower()))
            if desc_words & action_verbs:
                actionable_count += 1

        if num_tasks > 0 and actionable_count == num_tasks:
            score_act += 0.5
            strengths.append("Strong operational framing: all tasks use clear directive verbs and bounded scopes.")
        else:
            score_act += 0.25

        # 3c. Explicit boundaries (0.5 pt)
        score_act += 0.5

        # -------------------------------------------------------------
        # 4. Dimension: Schema & Operational Constraints (Weight: 1.5 pts)
        # -------------------------------------------------------------
        score_schema = 0.0

        # 4a. Research brief populated (0.4 pt)
        if isinstance(research_brief_str, str) and len(research_brief_str.strip()) > 20:
            score_schema += 0.4
        else:
            weaknesses.append("Output research_brief field is missing or empty.")

        # 4b. Status is "pending" (0.4 pt)
        invalid_statuses = [t.get("status") for t in tasks if t.get("status") != "pending"]
        if num_tasks > 0 and len(invalid_statuses) == 0:
            score_schema += 0.4
            strengths.append("Operational constraint met: all tasks initialized to 'pending'.")
        else:
            weaknesses.append(f"Task status constraint violated: {invalid_statuses}")

        # 4c. Result is null (0.35 pt)
        non_null_results = [t.get("result") for t in tasks if t.get("result") is not None]
        if len(non_null_results) == 0:
            score_schema += 0.35
            strengths.append("Operational constraint met: all task results initialized to null.")
        else:
            weaknesses.append("Task result was prematurely populated.")

        # 4d. Final summary is null (0.35 pt)
        if final_summary is None:
            score_schema += 0.35
            strengths.append("Operational constraint met: final_summary initialized to null.")
        else:
            weaknesses.append("final_summary was populated prematurely instead of being null.")

        # -------------------------------------------------------------
        # 5. Dimension: Scope & Edge Case Coverage (Weight: 1.5 pts)
        # -------------------------------------------------------------
        score_scope = 0.0

        # Check keyword coverage from brief in task descriptions
        brief_lower = brief.lower()
        combined_tasks_lower = " ".join(task_descriptions).lower()

        # Extract core domain nouns/keywords from brief
        core_sections = re.findall(r'(?:#*\s*(?:Scope|Delegation Suggestions|Edge Cases and Anomalies))(.*?)(?:#*\s*(?:Expected Deliverable|Assumptions|Clarification Needed|Self-Evaluation)|\Z)', brief, re.DOTALL)
        core_text = " ".join(core_sections) if core_sections else brief
        bullet_points = re.findall(r'[•\-]\s*([A-Za-z0-9\s&,/]+):', core_text)

        matched_bullets = 0
        for bp in bullet_points:
            bp_clean = bp.strip().lower()
            # check if at least one key term from bullet title appears in combined tasks
            words = [w for w in re.findall(r'\b\w+\b', bp_clean) if len(w) > 3 and w not in {"with", "from", "into", "over", "such", "than"}]
            if any(w in combined_tasks_lower for w in words):
                matched_bullets += 1

        total_bullets = len(bullet_points)
        if total_bullets > 0:
            coverage_ratio = matched_bullets / total_bullets
            if coverage_ratio >= 0.75:
                score_scope += 1.5
                strengths.append(f"Extensive coverage of brief's delegation suggestions & edge cases ({matched_bullets}/{total_bullets} focus areas referenced).")
            elif coverage_ratio >= 0.5:
                score_scope += 1.1
                strengths.append(f"Moderate coverage of brief's delegation suggestions ({matched_bullets}/{total_bullets} focus areas referenced).")
            else:
                score_scope += 0.7
                weaknesses.append(f"Low coverage of suggested focus areas ({matched_bullets}/{total_bullets} mapped).")
        else:
            score_scope += 1.4

        # -------------------------------------------------------------
        # Aggregate Final Score
        # -------------------------------------------------------------
        total_score = round(score_lb + score_decomp + score_act + score_schema + score_scope, 1)
        total_score = max(0.0, min(10.0, total_score))

        # Generate brief reason for the rating
        lb_status = "strictly balanced" if load_delta <= 1 and (num_tasks < 3 or len(active_agents) == 3) else "suboptimally balanced"
        reason = (
            f"Supervisor achieved an overall rating of {total_score}/10 by successfully decomposing the {category} research brief "
            f"into {num_tasks} actionable subtopics with {lb_status} delegation across "
            f"{len(active_agents)} research agents ({', '.join([f'{a}: {agent_counts[a]}' for a in VALID_AGENTS])}), "
            f"adhering to strict Pydantic output schemas and operational constraints (pending status, null results/summary)."
        )

        if len(weaknesses) > 0:
            improvements.append(f"Address identified areas: {'; '.join(weaknesses[:2])}")
        else:
            improvements.append("Maintain high prompt alignment and strict load balancing across all complexity categories.")

        return {
            "case_id": case_id,
            "category": category,
            "overall_score": total_score,
            "dimensions": {
                "load_balancing": round(score_lb, 2),
                "context_clustering": round(score_decomp, 2),
                "actionability": round(score_act, 2),
                "schema_constraints": round(score_schema, 2),
                "scope_coverage": round(score_scope, 2),
            },
            "metrics": {
                "task_count": num_tasks,
                "agent_distribution": agent_counts,
                "load_delta": load_delta,
                "all_agents_utilized": len(active_agents) == 3 if num_tasks >= 3 else True,
                "avg_words_per_task": round(avg_words, 1),
            },
            "reason": reason,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "improvements": improvements,
        }
