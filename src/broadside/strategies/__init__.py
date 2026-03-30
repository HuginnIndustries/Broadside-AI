"""Scatter strategies and synthesis strategies.

Scatter strategies control how inputs vary across agents.
Synthesis strategies control how outputs are collapsed.

Research-backed defaults (ACL 2025, Kaesberg et al.):
- Consensus works best for knowledge tasks
- Voting works best for reasoning/classification tasks
- LLM synthesis is the general-purpose fallback
"""
