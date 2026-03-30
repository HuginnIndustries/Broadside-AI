# Benchmark Results

**Model:** gemma3:1b  
**Backend:** ollama  
**Agents per scatter:** 3  
**Date:** 2026-03-30 06:18 UTC  

## Results

| Task | Parallel | Sequential | Speedup | Tokens (scatter+synth) | Cost vs 1 call | Diversity |
|------|----------|------------|---------|----------------------|----------------|-----------|
| creative_pitch | 17.3s | 16.1s | 0.93x | 509+1146=1655 | 9.2x | 0.755 |
| analytical_comparison | 158.1s | 190.3s | 1.20x | 3927+5045=8972 | 6.3x | 0.732 |
| classification | 12.0s | 10.4s | 0.87x | 509+676=1185 | 7.1x | 0.750 |
| summarization | 30.6s | 42.9s | 1.40x | 841+1246=2087 | 6.8x | 0.803 |
| code_review | 187.9s | 182.6s | 0.97x | 4208+5230=9438 | 6.6x | 0.735 |
| **Average** | | | **1.08x** | | **7.2x** | **0.755** |

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