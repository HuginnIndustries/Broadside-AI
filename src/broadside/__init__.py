"""Broadside: parallel LLM agent orchestration using scatter/gather."""

from broadside.task import Task
from broadside.scatter import scatter
from broadside.gather import gather
from broadside.synthesize import synthesize
from broadside.run import run

__version__ = "0.1.0"

__all__ = ["Task", "scatter", "gather", "synthesize", "run"]
