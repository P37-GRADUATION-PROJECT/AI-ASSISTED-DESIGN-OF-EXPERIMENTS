# Çimyapan (2024): ultrasound extraction of soluble protein from three microalgae

39 runs (3 species × 13) transcribed from a published GTU MSc thesis. Used as
prior data (warm start / transfer learning, E2) and for planning the E3 case
study.

| | |
| --- | --- |
| Source | Çimyapan, Ş. (2024). MSc thesis, Institute of Biotechnology, Gebze Technical University. Advisor: Assoc. Prof. Dr. Müge İşleten Hoşoğlu. Tables 3.1–3.3 (pp. 29, 31, 33). |
| Received | 2026-10-21 from the GTU Institute of Biotechnology |
| Factors | Biomass concentration (g/L), extraction time (min) |
| Response | Total soluble protein in the supernatant (g/L), Lowry assay, BSA standard |
| Equipment | Probe ultrasonic homogenizer, Bandelin HD 2070 (9 × 10 % cycle, 45–55 % power) |
| Not reported | pH and temperature during extraction; protein content of the biomasses |

The values are copied exactly as printed and are never edited in place.
`scripts/build_cimyapan2024.py` holds the transcription and writes both files
in this folder; `tests/test_cimyapan2024.py` checks them.

## Files

- `extraction_runs.csv`: one row per run.
- `extraction_runs.json`: source, method, flag definitions, per-species summary, CSV checksum.
- `yield_vs_biomass.png`: made by `scripts/plot_cimyapan2024.py`.

## Columns

| Column | Meaning |
| --- | --- |
| `biomass_g_L`, `time_min`, `soluble_protein_g_L` | As printed in the thesis |
| `yield_mg_per_g` | Derived: 1000 × protein (g/L) / biomass (g/L) |
| `biomass_coded`, `time_coded` | Recomputed from the actual values: ±1 factorial, ±1.414 axial |
| `*_coded_printed` | Coded values as printed (axial points appear as ±1) |
| `point_type` | `factorial`, `axial` or `centre` |
| `use_in_model` | 0 = left out by default (see flags), 1 = used |
| `flags` | Semicolon-separated codes, defined below |

## Data-quality flags

| Flag | Runs | What it means |
| --- | --- | --- |
| `suspect_value` | S. limacinum 13 | Centre run is 0.108 g/L; the other four centre runs are 1.099–1.133 g/L. Probably a typo. **Left out by default** until the raw file confirms it. |
| `near_zero` | A. protothecoides 3 | 0.0001 g/L, likely below the Lowry quantification limit. |
| `time_level_mismatch` | S. platensis 12, 13 | Low time level printed as both 5 and 2 min; axial 2.29 min does not fit a 5–20 min CCD (1.89 min). |
| `centre_time_typo` | S. platensis 1–7 | Centre time 12.30 min; the midpoint of 5–20 min is 12.50 min. |
| `axial_time_asymmetric` | A. protothecoides and S. limacinum 4, 10 | 10.22 / 48.18 min are not symmetric around 27.5 min (expected 9.82 / 45.18). |

**Design label.** The thesis calls the design Box–Behnken. With two factors
and 4 factorial + 4 axial + 5 centre runs, it is a central composite design
(Box–Behnken needs at least three factors).

## What the data says (summary from `extraction_runs.json`)

| Species | Centre replicates, mean ± SD (CV) | Best g/L (biomass, time) | Best yield (biomass, time) |
| --- | --- | --- | --- |
| S. platensis | 1.002 ± 0.118 g/L (11.8 %) | 2.05 g/L (50 g/L, 20 min) | 70.0 mg/g (10 g/L, 20 min) |
| A. protothecoides | 0.646 ± 0.060 g/L (9.3 %) | 1.12 g/L (58.3 g/L, 27.5 min) | 24.1 mg/g (30 g/L, 27.5 min) |
| S. limacinum | 1.116 ± 0.014 g/L (1.3 %, 4 runs) | 1.75 g/L (58.3 g/L, 27.5 min) | 48.5 mg/g (10 g/L, 40 min) |

- Soluble protein in g/L rises with biomass for every species, so a g/L
  optimum always sits at the top of the biomass range.
- Yield per gram of biomass falls with biomass for S. platensis and
  S. limacinum. For A. protothecoides it is flat (about 17–24 mg/g from
  10 g/L upwards). Choosing g/L or yield as the response therefore changes where the
  optimum is.
- Measurement noise differs a lot between species (CV 1–12 % at the centre
  point), which matters for the noise setting of the optimizer.

## Limits for reuse

The planned case study uses an ultrasonic **bath**, not a probe, and may add a
third factor (pH or temperature) that these runs held fixed at an unreported
value. Treat this data as a *related* task (transfer learning), not as earlier
runs of the same experiment.
