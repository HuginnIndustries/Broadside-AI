"""Broadside: parallel LLM agent orchestration using scatter/gather."""

from broadside_ai.gather import gather
from broadside_ai.run import run, run_sync
from broadside_ai.scatter import scatter
from broadside_ai.synthesize import synthesize
from broadside_ai.task import Task

__version__ = "0.1.0"

__all__ = ["Task", "scatter", "gather", "synthesize", "run", "run_sync"]
