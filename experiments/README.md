# experiments

| ID | Question | Target |
| --- | --- | --- |
| E1 | Does BO reach 95% of the best result in fewer runs than the classical design? | At least 30% fewer runs, median over 20 seeds |
| E2 | How many runs do warm start / LLM priors save over cold-start BO? | Paired test across seeds |
| E3 | Does the approach hold up in the real lab? | Comparison with replicates |

Each experiment gets its own folder with a config file (including seeds) and a
results summary. Large run outputs go in `runs/`, which is git-ignored.
