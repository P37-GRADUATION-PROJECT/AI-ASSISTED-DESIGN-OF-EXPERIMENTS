## Head to head (same number of runs)

| Problem | Noise | Classical design | Runs | Classical score | BO score (runs) | BO − classical (p) | Classical ≥ 0.95 | BO runs to 0.95 (seeds) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Broad peak, 3 factors | 0.1 | Box–Behnken + quadratic model | 16 | 0.98 (0.96–0.98) | 0.92 (0.86–0.95) (16) | -0.06 (p = 0.0001) | 90% | 22 (90%) |
| Broad peak, 3 factors | 0.1 | CCD (face-centred) + quadratic model | 18 | 0.98 (0.97–0.99) | 0.94 (0.92–0.97) (20) | -0.04 (p = 0.0005) | 95% | 22 (90%) |
| Broad peak, 3 factors | 0.3 | Box–Behnken + quadratic model | 16 | 0.86 (0.81–0.95) | 0.76 (0.60–0.91) (16) | -0.03 (p = 0.45) | 25% | not reached (30%) |
| Broad peak, 3 factors | 0.3 | CCD (face-centred) + quadratic model | 18 | 0.75 (0.66–0.85) | 0.86 (0.64–0.90) (20) | +0.07 (p = 0.45) | 5% | not reached (30%) |
| Broad peak, 4 factors | 0.1 | Box–Behnken + quadratic model | 28 | 0.99 (0.97–1.00) | 0.94 (0.92–0.97) (28) | -0.04 (p = 0.033) | 75% | 34 (65%) |
| Broad peak, 4 factors | 0.1 | CCD (face-centred) + quadratic model | 28 | 0.94 (0.88–0.96) | 0.94 (0.92–0.97) (28) | -0.01 (p = 0.62) | 45% | 34 (65%) |
| Broad peak, 4 factors | 0.3 | Box–Behnken + quadratic model | 28 | 0.72 (0.43–0.87) | 0.76 (0.66–0.91) (28) | +0.05 (p = 0.25) | 5% | not reached (10%) |
| Broad peak, 4 factors | 0.3 | CCD (face-centred) + quadratic model | 28 | 0.44 (0.29–0.66) | 0.76 (0.66–0.91) (28) | +0.26 (p = 0.0003) | 0% | not reached (10%) |
| Narrow peak, 3 factors | 0.1 | Box–Behnken + quadratic model | 16 | 0.69 (0.62–0.75) | 0.84 (0.78–0.93) (16) | +0.15 (p = 0.0017) | 0% | 24 (90%) |
| Narrow peak, 3 factors | 0.1 | CCD (face-centred) + quadratic model | 18 | 0.55 (0.41–0.79) | 0.92 (0.86–0.96) (20) | +0.37 (p = 0.0003) | 5% | 24 (90%) |
| Narrow peak, 3 factors | 0.3 | Box–Behnken + quadratic model | 16 | 0.17 (-0.04–0.28) | 0.58 (0.33–0.80) (16) | +0.46 (p = 0.0049) | 0% | not reached (30%) |
| Narrow peak, 3 factors | 0.3 | CCD (face-centred) + quadratic model | 18 | -0.02 (-0.13–0.20) | 0.58 (0.34–0.84) (20) | +0.42 (p = 0) | 0% | not reached (30%) |
| Hartmann (4 bumps), 3 factors | 0.1 | Box–Behnken + quadratic model | 16 | -0.03 (-0.06–0.13) | 0.92 (0.87–0.95) (16) | +0.87 (p = 0) | 0% | 20 (90%) |
| Hartmann (4 bumps), 3 factors | 0.1 | CCD (face-centred) + quadratic model | 18 | 0.23 (-0.00–0.45) | 0.95 (0.91–0.97) (20) | +0.69 (p = 0) | 0% | 20 (90%) |
| Hartmann (4 bumps), 3 factors | 0.3 | Box–Behnken + quadratic model | 16 | 0.31 (-0.06–0.43) | 0.71 (0.57–0.91) (16) | +0.53 (p = 0) | 0% | not reached (30%) |
| Hartmann (4 bumps), 3 factors | 0.3 | CCD (face-centred) + quadratic model | 18 | -0.06 (-0.10–0.29) | 0.74 (0.48–0.90) (20) | +0.68 (p = 0) | 0% | not reached (30%) |

## All strategies

| Problem | Noise | Strategy | Runs | Score at 8 | at 16 | at 32 / at its runs | Runs to 0.95 (median) | Seeds reaching 0.95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Broad peak, 3 factors | 0.1 | BO (model's best run) | 32 | 0.75 (0.59–0.86) | 0.92 (0.86–0.95) | 0.98 (0.95–0.99) | 22 | 90% |
| Broad peak, 3 factors | 0.1 | BO (best measured run) | 32 | 0.75 (0.59–0.86) | 0.92 (0.86–0.95) | 0.96 (0.94–0.99) | 18.5 | 70% |
| Broad peak, 3 factors | 0.1 | Random | 32 | 0.65 (0.55–0.78) | 0.80 (0.62–0.88) | 0.85 (0.81–0.91) | not reached | 20% |
| Broad peak, 3 factors | 0.1 | Box–Behnken + quadratic model | 16 |  |  | 0.98 (0.96–0.98) | 16 | 90% |
| Broad peak, 3 factors | 0.1 | CCD (face-centred) + quadratic model | 18 |  |  | 0.98 (0.97–0.99) | 18 | 95% |
| Broad peak, 3 factors | 0.1 | Box–Behnken, best measured run | 15 |  |  | 0.51 (0.51–0.51) | not reached | 0% |
| Broad peak, 3 factors | 0.1 | CCD, best measured run | 17 |  |  | 0.51 (0.51–0.55) | not reached | 0% |
| Broad peak, 3 factors | 0.3 | BO (model's best run) | 32 | 0.67 (0.55–0.76) | 0.76 (0.60–0.91) | 0.84 (0.76–0.89) | not reached | 30% |
| Broad peak, 3 factors | 0.3 | BO (best measured run) | 32 | 0.67 (0.55–0.76) | 0.76 (0.60–0.91) | 0.85 (0.76–0.90) | not reached | 15% |
| Broad peak, 3 factors | 0.3 | Random | 32 | 0.57 (0.47–0.74) | 0.70 (0.56–0.81) | 0.75 (0.59–0.84) | not reached | 10% |
| Broad peak, 3 factors | 0.3 | Box–Behnken + quadratic model | 16 |  |  | 0.86 (0.81–0.95) | not reached | 25% |
| Broad peak, 3 factors | 0.3 | CCD (face-centred) + quadratic model | 18 |  |  | 0.75 (0.66–0.85) | not reached | 5% |
| Broad peak, 3 factors | 0.3 | Box–Behnken, best measured run | 15 |  |  | 0.51 (0.33–0.51) | not reached | 0% |
| Broad peak, 3 factors | 0.3 | CCD, best measured run | 17 |  |  | 0.51 (0.51–0.58) | not reached | 0% |
| Broad peak, 4 factors | 0.1 | BO (model's best run) | 40 | 0.71 (0.53–0.77) | 0.91 (0.86–0.94) | 0.94 (0.91–0.97) | 34 | 65% |
| Broad peak, 4 factors | 0.1 | BO (best measured run) | 40 | 0.71 (0.53–0.77) | 0.90 (0.82–0.94) | 0.94 (0.90–0.96) | 37.5 | 55% |
| Broad peak, 4 factors | 0.1 | Random | 40 | 0.55 (0.45–0.66) | 0.61 (0.53–0.73) | 0.76 (0.71–0.84) | not reached | 5% |
| Broad peak, 4 factors | 0.1 | Box–Behnken + quadratic model | 28 |  |  | 0.99 (0.97–1.00) | 28 | 75% |
| Broad peak, 4 factors | 0.1 | CCD (face-centred) + quadratic model | 28 |  |  | 0.94 (0.88–0.96) | not reached | 45% |
| Broad peak, 4 factors | 0.1 | Box–Behnken, best measured run | 27 |  |  | 0.50 (0.50–0.50) | not reached | 0% |
| Broad peak, 4 factors | 0.1 | CCD, best measured run | 27 |  |  | 0.64 (0.50–0.64) | not reached | 0% |
| Broad peak, 4 factors | 0.3 | BO (model's best run) | 40 | 0.62 (0.53–0.72) | 0.74 (0.62–0.86) | 0.77 (0.66–0.91) | not reached | 10% |
| Broad peak, 4 factors | 0.3 | BO (best measured run) | 40 | 0.62 (0.53–0.72) | 0.74 (0.62–0.86) | 0.77 (0.68–0.91) | not reached | 10% |
| Broad peak, 4 factors | 0.3 | Random | 40 | 0.65 (0.48–0.70) | 0.69 (0.57–0.75) | 0.70 (0.57–0.75) | not reached | 0% |
| Broad peak, 4 factors | 0.3 | Box–Behnken + quadratic model | 28 |  |  | 0.72 (0.43–0.87) | not reached | 5% |
| Broad peak, 4 factors | 0.3 | CCD (face-centred) + quadratic model | 28 |  |  | 0.44 (0.29–0.66) | not reached | 0% |
| Broad peak, 4 factors | 0.3 | Box–Behnken, best measured run | 27 |  |  | 0.50 (0.41–0.50) | not reached | 0% |
| Broad peak, 4 factors | 0.3 | CCD, best measured run | 27 |  |  | 0.50 (0.48–0.50) | not reached | 0% |
| Narrow peak, 3 factors | 0.1 | BO (model's best run) | 32 | 0.59 (0.47–0.66) | 0.84 (0.78–0.93) | 0.98 (0.96–0.99) | 24 | 90% |
| Narrow peak, 3 factors | 0.1 | BO (best measured run) | 32 | 0.59 (0.47–0.66) | 0.84 (0.78–0.93) | 0.96 (0.93–0.98) | 21.5 | 80% |
| Narrow peak, 3 factors | 0.1 | Random | 32 | 0.63 (0.43–0.70) | 0.68 (0.49–0.84) | 0.79 (0.63–0.86) | not reached | 5% |
| Narrow peak, 3 factors | 0.1 | Box–Behnken + quadratic model | 16 |  |  | 0.69 (0.62–0.75) | not reached | 0% |
| Narrow peak, 3 factors | 0.1 | CCD (face-centred) + quadratic model | 18 |  |  | 0.55 (0.41–0.79) | not reached | 5% |
| Narrow peak, 3 factors | 0.1 | Box–Behnken, best measured run | 15 |  |  | 0.34 (0.34–0.34) | not reached | 0% |
| Narrow peak, 3 factors | 0.1 | CCD, best measured run | 17 |  |  | 0.37 (0.34–0.42) | not reached | 0% |
| Narrow peak, 3 factors | 0.3 | BO (model's best run) | 32 | 0.45 (0.12–0.56) | 0.58 (0.33–0.80) | 0.82 (0.67–0.93) | not reached | 30% |
| Narrow peak, 3 factors | 0.3 | BO (best measured run) | 32 | 0.45 (0.12–0.56) | 0.58 (0.33–0.80) | 0.81 (0.59–0.93) | not reached | 30% |
| Narrow peak, 3 factors | 0.3 | Random | 32 | 0.57 (0.29–0.73) | 0.66 (0.50–0.72) | 0.75 (0.64–0.81) | not reached | 0% |
| Narrow peak, 3 factors | 0.3 | Box–Behnken + quadratic model | 16 |  |  | 0.17 (-0.04–0.28) | not reached | 0% |
| Narrow peak, 3 factors | 0.3 | CCD (face-centred) + quadratic model | 18 |  |  | -0.02 (-0.13–0.20) | not reached | 0% |
| Narrow peak, 3 factors | 0.3 | Box–Behnken, best measured run | 15 |  |  | 0.34 (0.17–0.34) | not reached | 0% |
| Narrow peak, 3 factors | 0.3 | CCD, best measured run | 17 |  |  | 0.34 (-0.05–0.34) | not reached | 0% |
| Hartmann (4 bumps), 3 factors | 0.1 | BO (model's best run) | 32 | 0.81 (0.64–0.90) | 0.92 (0.87–0.95) | 0.98 (0.95–0.99) | 20 | 90% |
| Hartmann (4 bumps), 3 factors | 0.1 | BO (best measured run) | 32 | 0.81 (0.64–0.90) | 0.93 (0.88–0.95) | 0.96 (0.92–0.99) | 25 | 70% |
| Hartmann (4 bumps), 3 factors | 0.1 | Random | 32 | 0.56 (0.38–0.72) | 0.60 (0.55–0.84) | 0.83 (0.59–0.91) | not reached | 10% |
| Hartmann (4 bumps), 3 factors | 0.1 | Box–Behnken + quadratic model | 16 |  |  | -0.03 (-0.06–0.13) | not reached | 0% |
| Hartmann (4 bumps), 3 factors | 0.1 | CCD (face-centred) + quadratic model | 18 |  |  | 0.23 (-0.00–0.45) | not reached | 0% |
| Hartmann (4 bumps), 3 factors | 0.1 | Box–Behnken, best measured run | 15 |  |  | 0.52 (0.50–0.52) | not reached | 0% |
| Hartmann (4 bumps), 3 factors | 0.1 | CCD, best measured run | 17 |  |  | 0.43 (0.28–0.43) | not reached | 0% |
| Hartmann (4 bumps), 3 factors | 0.3 | BO (model's best run) | 32 | 0.64 (0.50–0.75) | 0.71 (0.57–0.91) | 0.74 (0.62–0.90) | not reached | 30% |
| Hartmann (4 bumps), 3 factors | 0.3 | BO (best measured run) | 32 | 0.64 (0.50–0.75) | 0.71 (0.57–0.91) | 0.72 (0.62–0.88) | not reached | 25% |
| Hartmann (4 bumps), 3 factors | 0.3 | Random | 32 | 0.57 (0.41–0.75) | 0.63 (0.41–0.78) | 0.64 (0.55–0.74) | not reached | 5% |
| Hartmann (4 bumps), 3 factors | 0.3 | Box–Behnken + quadratic model | 16 |  |  | 0.31 (-0.06–0.43) | not reached | 0% |
| Hartmann (4 bumps), 3 factors | 0.3 | CCD (face-centred) + quadratic model | 18 |  |  | -0.06 (-0.10–0.29) | not reached | 0% |
| Hartmann (4 bumps), 3 factors | 0.3 | Box–Behnken, best measured run | 15 |  |  | 0.44 (0.02–0.44) | not reached | 0% |
| Hartmann (4 bumps), 3 factors | 0.3 | CCD, best measured run | 17 |  |  | 0.28 (-0.00–0.43) | not reached | 0% |
