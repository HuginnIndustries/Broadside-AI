"""Broadside: parallel LLM agent orchestration using scatter/gather."""

from broadside.gather import gather
from broadside.run import run, run_sync
from broadside.scatter import scatter
from broadside.synthesize import synthesize
from broadside.task import Task

__version__ = "0.1.0"

__all__ = ["Task", "scatter", "gather", "synthesize", "run", "run_sync"]
