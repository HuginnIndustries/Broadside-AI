# Benchmark Results

**Model:** claude-sonnet-4-20250514  
**Backend:** anthropic  
**Agents per scatter:** 3  
**Date:** 2026-03-30 05:41 UTC  

## Results

| Task | Parallel | Sequential | Speedup | Tokens (scatter+synth) | Cost vs 1 call | Diversity |
|------|----------|------------|---------|----------------------|----------------|-----------|
| creative_pitch | 8.4s | 19.8s | 2.36x | 644+1143=1787 | 8.6x | 0.767 |
| analytical_comparison | 35.3s | 78.8s | 2.23x | 4819+5653=10472 | 6.8x | 0.734 |
| classification | 4.6s | 11.4s | 2.48x | 602+705=1307 | 6.5x | 0.640 |
| summarization | 10.7s | 27.9s | 2.59x | 1072+1504=2576 | 7.2x | 0.735 |
| code_review | 17.3s | 50.8s | 2.94x | 2967+3440=6407 | 5.4x | 0.651 |
| **Average** | | | **2.52x** | | **6.9x** | **0.705** |

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