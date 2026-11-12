"""Summarize loso_thesis.py output: table (Markdown + CSV) and figure.

Usage:
    python experiments/e2/summarize_loso.py experiments/e2/results/loso_thesis_runs.csv

Writes next to the input: loso_thesis_summary.csv, loso_thesis_summary.md,
loso_thesis.png. Per species, objective and mode: median and IQR of the score
after 4, 8 and 12 runs, and the median number of runs to reach 0.95.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loso_thesis import SimulatedLab, load_rows  # noqa: E402

SPECIES = [
    ("S_platensis", "S. platensis"),
    ("A_protothecoides", "A. protothecoides"),
    ("S_limacinum", "S. limacinum"),
]
OBJECTIVES = [("protein_g_L", "Soluble protein (g/L)"), ("yield_mg_g", "Yield (mg/g biomass)")]
MODES = [("cold", "cold start", "#2a78d6"), ("warm", "warm start", "#1baf7a")]
INK, MUTED, GRID = "#1E293B", "#64748B", "#E2E8F0"
CHECKPOINTS = (4, 8, 12)


def load(path: Path):
    curves: dict[tuple, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    with path.open() as f:
        for r in csv.DictReader(f):
            key = (r["species"], r["objective"], r["mode"])
            curves[key][int(r["seed"])].append(float(r["score"]))
    out = {}
    for k, v in curves.items():
        full = max(len(x) for x in v.values())
        done = [s for s in sorted(v) if len(v[s]) == full]
        if len(done) < len(v):
            print(f"note: {k}: {len(v) - len(done)} incomplete seed(s) left out", file=sys.stderr)
        out[k] = np.array([v[s] for s in done])
    return out


def runs_to(scores: np.ndarray, target: float = 0.95) -> list[float]:
    out = []
    for row in scores:
        hit = np.nonzero(row >= target)[0]
        out.append(float(hit[0] + 1) if hit.size else np.inf)
    return out


def main(argv: list[str]) -> int:
    path = Path(argv[1])
    data = load(path)
    # How much there is to find, compared with the measurement noise. A score
    # is only meaningful when the optimum stands out from a random run by more
    # than the noise; otherwise the problem is "flat" and the score just amplifies noise.
    signal = {}
    thesis = load_rows()
    for sp, _ in SPECIES:
        lab = SimulatedLab(thesis, sp)
        for obj, col in (("protein_g_L", "soluble_protein"), ("yield_mg_g", "yield_mg_per_g")):
            best, med = lab.ref[col]
            vals = lab.true(lab.grid, col)
            b_opt = lab.grid[int(np.argmax(vals))][0]
            noise = lab.noise_sd if col == "soluble_protein" else 1000 * lab.noise_sd / b_opt
            signal[(sp, obj)] = (best - med, noise)
    rows = []
    for sp, _ in SPECIES:
        for obj, _ in OBJECTIVES:
            for mode, _, _ in MODES:
                s = data.get((sp, obj, mode))
                if s is None:
                    continue
                spread, noise = signal[(sp, obj)]
                rec = {"species": sp, "objective": obj, "mode": mode, "seeds": len(s)}
                rec["optimum_minus_median"] = round(spread, 3)
                rec["noise_sd_at_optimum"] = round(noise, 3)
                rec["flat"] = "yes" if spread < 2 * noise else "no"
                for n in CHECKPOINTS:
                    q1, med, q3 = np.percentile(s[:, n - 1], [25, 50, 75])
                    rec[f"median_at_{n}"] = round(float(med), 3)
                    rec[f"iqr_at_{n}"] = f"{q1:.2f}-{q3:.2f}"
                rt = runs_to(s)
                med_rt = float(np.median(rt))
                rec["median_runs_to_0.95"] = "not reached" if np.isinf(med_rt) else med_rt
                rec["share_reached_0.95"] = f"{np.mean(np.isfinite(rt)):.0%}"
                rows.append(rec)

    # Paired comparison at 8 runs: cold and warm use the same seeds and the same
    # noise draws, so seed i of one is paired with seed i of the other.
    from scipy.stats import wilcoxon

    for r in rows:
        if r["mode"] != "warm":
            continue
        cold, warm = (
            data[(r["species"], r["objective"], "cold")],
            data[(r["species"], r["objective"], "warm")],
        )
        diff = warm[:, 7] - cold[:, 7]
        r["median_diff_at_8"] = round(float(np.median(diff)), 3)
        r["wilcoxon_p_at_8"] = (
            round(float(wilcoxon(warm[:, 7], cold[:, 7]).pvalue), 4) if np.any(diff) else 1.0
        )
    for r in rows:
        r.setdefault("median_diff_at_8", "")
        r.setdefault("wilcoxon_p_at_8", "")

    out_csv = path.with_name("loso_thesis_summary.csv")
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    md = [
        "| Species | Objective | Start | Score at 4 runs | at 8 runs | at 12 runs "
        "| Runs to 0.95 (median) | Seeds reaching 0.95 | Warm − cold at 8 runs (p) "
        "| Optimum − median / noise SD |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        cells = [r["species"].replace("_", ". ", 1), r["objective"], r["mode"]]
        cells += [f"{r[f'median_at_{n}']:.2f} ({r[f'iqr_at_{n}']})" for n in CHECKPOINTS]
        cells += [str(r["median_runs_to_0.95"]), r["share_reached_0.95"]]
        cells.append(
            f"{r['median_diff_at_8']:+.2f} (p = {r['wilcoxon_p_at_8']:.3g})"
            if r["mode"] == "warm"
            else ""
        )
        ratio = r["optimum_minus_median"] / r["noise_sd_at_optimum"]
        cells.append(
            f"{ratio:.1f}" + (" (flat: score not meaningful)" if r["flat"] == "yes" else "")
        )
        md.append("| " + " | ".join(cells) + " |")
    out_md = path.with_name("loso_thesis_summary.md")
    out_md.write_text("\n".join(md) + "\n")

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "text.color": INK})
    fig, axes = plt.subplots(2, 3, figsize=(10.5, 6), sharex=True, sharey=True)
    for i, (obj, obj_label) in enumerate(OBJECTIVES):
        for j, (sp, sp_label) in enumerate(SPECIES):
            ax = axes[i, j]
            ends = []
            for mode, label, color in MODES:
                s = data.get((sp, obj, mode))
                if s is None:
                    continue
                n = np.arange(1, s.shape[1] + 1)
                q1, med, q3 = np.percentile(s, [25, 50, 75], axis=0)
                ax.fill_between(n, q1, q3, color=color, alpha=0.15, linewidth=0)
                ax.plot(n, med, color=color, linewidth=2, label=label)
                ends.append([label, float(n[-1]), float(med[-1])])
            # keep the two end labels at least 0.1 apart so they never overlap
            if len(ends) == 2 and abs(ends[0][2] - ends[1][2]) < 0.1:
                lo, hi = sorted(ends, key=lambda e: e[2])
                mid = (lo[2] + hi[2]) / 2
                lo[2], hi[2] = mid - 0.05, mid + 0.05
            for label, x_end, y_lab in ends:
                ax.annotate(
                    label,
                    (x_end, y_lab),
                    xytext=(4, 0),
                    textcoords="offset points",
                    va="center",
                    fontsize=7.5,
                    color=INK,
                )
            ax.axhline(0.95, color=MUTED, linewidth=0.8, linestyle="--")
            spread, noise = signal[(sp, obj)]
            if spread < 2 * noise:
                ax.text(
                    0.5,
                    0.08,
                    f"Flat surface: optimum − median = {spread / noise:.1f} × noise SD.\n"
                    "Score not meaningful; warm start lies below the axis.",
                    transform=ax.transAxes,
                    ha="center",
                    fontsize=7.5,
                    color=INK,
                    bbox={"facecolor": "white", "edgecolor": GRID, "boxstyle": "round,pad=0.4"},
                )
            for b in (4.5, 8.5):
                ax.axvline(b, color=GRID, linewidth=0.8)
            ax.grid(axis="y", color=GRID, linewidth=0.6)
            ax.set_axisbelow(True)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            ax.tick_params(colors=MUTED)
            ax.set_xlim(1, 14.5)
            ax.set_ylim(-0.5, 1.08)
            ax.set_xticks([4, 8, 12])
            if i == 0:
                ax.set_title(sp_label, fontsize=10, fontstyle="italic")
            if j == 0:
                ax.set_ylabel(f"{obj_label}\nscore (1 = optimum)")
            if i == 1:
                ax.set_xlabel("Runs (batches of 4)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", frameon=False, ncol=2)
    fig.suptitle(
        "Leave-one-species-out: BO with and without the other species as warm start",
        x=0.02,
        ha="left",
        fontsize=11,
    )
    fig.text(
        0.02,
        0.005,
        "Median and IQR over seeds. Simulated lab = quadratic fit to the held-out species "
        "(Çimyapan 2024) + centre-run noise. Dashed line: 0.95. Preliminary, 2 factors.",
        fontsize=7.5,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    out_png = path.with_name("loso_thesis.png")
    fig.savefig(out_png, dpi=200)
    print(f"wrote {out_csv.name}, {out_md.name}, {out_png.name}")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
