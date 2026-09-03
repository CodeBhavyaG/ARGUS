"""Shim module that re-exports from the original evaluator_supervisor module."""

from eval.evaluator_supervisor import SupervisorEvaluator, VALID_AGENTS

__all__ = ["SupervisorEvaluator", "VALID_AGENTS"]