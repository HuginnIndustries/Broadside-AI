# Benchmark Results

**Model:** nemotron-3-super  
**Backend:** ollama  
**Agents per scatter:** 3  
**Date:** 2026-03-30 05:21 UTC  

## Results

| Task | Parallel | Sequential | Speedup | Tokens (scatter+synth) | Cost vs 1 call | Diversity |
|------|----------|------------|---------|----------------------|----------------|-----------|
| creative_pitch | 6.3s | 30.1s | 4.80x | 694+1737=2431 | 10.1x | 0.827 |
| analytical_comparison | 56.9s | 54.4s | 0.96x | 4788+6364=11152 | 7.1x | 0.764 |
| classification | 4.0s | 13.8s | 3.45x | 640+927=1567 | 7.0x | 0.603 |
| summarization | 10.3s | 11.9s | 1.15x | 1219+2343=3562 | 8.9x | 0.801 |
| code_review | 108.6s | 102.3s | 0.94x | 10582+12538=23120 | 7.3x | 0.737 |
| **Average** | | | **2.26x** | | **8.1x** | **0.746** |

## How to read this

**Speedup** = sequential wall-clock / parallel wall-clock. Values above 1.0 mean parallel is faster. With 3 agents on a cloud backend, theoretical max is 3.0x.

**Cost vs 1 call** = total tokens (scatter + synthesis) / tokens for a single LLM call. This is the real cost question: how much more do you pay for scatter/gather vs just prompting once? Scatter alone costs ~3x; the LLM synthesis strategy adds another ~1x on top.

**Diversity** = average pairwise Jaccard distance (word-level) across scatter outputs. 0.0 = identical, 1.0 = completely different. Higher diversity means the scatter is surfacing genuinely different perspectives.

## Reproduce

```bash
pip install broadside
python benchmarks/suite.py
```

Results are written to `benchmarks/results/`.