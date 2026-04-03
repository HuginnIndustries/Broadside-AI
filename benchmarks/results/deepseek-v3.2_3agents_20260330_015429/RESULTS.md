# Benchmark Results

**Model:** deepseek-v3.2  
**Backend:** ollama  
**Agents per scatter:** 3  
**Date:** 2026-03-30 05:54 UTC  

## Results

| Task | Parallel | Sequential | Speedup | Tokens (scatter+synth) | Cost vs 1 call | Diversity |
|------|----------|------------|---------|----------------------|----------------|-----------|
| creative_pitch | 16.8s | 28.3s | 1.68x | 1039+1370=2409 | 7.6x | 0.840 |
| analytical_comparison | 70.5s | 119.7s | 1.70x | 4527+3091=7618 | 4.6x | 0.731 |
| classification | 22.0s | 32.7s | 1.48x | 1531+755=2286 | 4.3x | 0.600 |
| summarization | 29.6s | 26.8s | 0.91x | 1363+1334=2697 | 6.6x | 0.812 |
| code_review | 115.0s | 175.3s | 1.52x | 8258+5345=13603 | 5.2x | 0.674 |
| **Average** | | | **1.46x** | | **5.7x** | **0.732** |

## How to read this

**Speedup** = sequential wall-clock / parallel wall-clock. Values above 1.0 mean parallel is faster. With 3 agents on a cloud backend, theoretical max is 3.0x.

**Cost vs 1 call** = total tokens (scatter + synthesis) / tokens for a single LLM call. This is the real cost question: how much more do you pay for scatter/gather vs just prompting once? Scatter alone costs ~3x; the LLM synthesis strategy adds another ~1x on top.

**Diversity** = average pairwise Jaccard distance (word-level) across scatter outputs. 0.0 = identical, 1.0 = completely different. Higher diversity means the scatter is surfacing genuinely different perspectives.

## Reproduce

```bash
pip install broadside-ai
python benchmarks/suite.py
```

Results are written to `benchmarks/results/`.
