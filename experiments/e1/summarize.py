"""Summarize benchmark.py output: tables (Markdown + CSV) and one figure.

Usage:
    python experiments/e1/summarize.py experiments/e1/results/e1_runs.csv

Writes next to the input: e1_summary.csv, e1_summary.md, e1_head_to_head.csv,
e1.png.

- Summary: per problem, noise and strategy, the median (IQR) score after
  8, 16 and 32 runs (classical: at the runs it uses) and how many runs it took
  to reach 0.95 (median over seeds; "not reached" if most seeds never got there).
- Head to head: each classical design against BO with the same number of runs
  (BO is read at the first batch end with at least as many runs). Paired by
  seed, Wilcoxon signed-rank test.
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
from scipy.stats import wilcoxon  # noqa: E402

PROBLEM_LABELS = {
    "peak3": "Broad peak, 3 factors",
    "peak4": "Broad peak, 4 factors",
    "peak3_narrow": "Narrow peak, 3 factors",
    "hartmann3": "Hartmann (4 bumps), 3 factors",
}
SEQUENTIAL = ("bo", "bo_best_run", "random")
CLASSICAL = ("bbd", "ccd_face")
LABELS = {
    "bo": "BO (model's best run)",
    "bo_best_run": "BO (best measured run)",
    "random": "Random",
    "bbd": "Box–Behnken + quadratic model",
    "ccd_face": "CCD (face-centred) + quadratic model",
    "bbd_best_run": "Box–Behnken, best measured run",
    "ccd_face_best_run": "CCD, best measured run",
}
INK, MUTED, GRID = "#1E293B", "#64748B", "#E2E8F0"
COLORS = {
    "bo": "#2a78d6",
    "bo_best_run": "#2a78d6",
    "random": "#94A3B8",
    "bbd": "#1F3A5F",
    "ccd_face": "#0F766E",
}
TARGET = 0.95


def load(path: Path):
    """{(problem, noise, strategy): {seed: {n_runs: score}}}"""
    data: dict = defaultdict(lambda: defaultdict(dict))
    with path.open() as f:
        for r in csv.DictReader(f):
            key = (r["problem"], float(r["noise"]), r["strategy"])
            data[key][int(r["seed"])][int(r["n_runs"])] = float(r["score"])
    return data


def matrix(curves: dict) -> tuple[np.ndarray, np.ndarray]:
    """(run counts, scores[seed, run]) for seeds that have every run count."""
    ns = sorted({n for c in curves.values() for n in c})
    seeds = [s for s in sorted(curves) if all(n in curves[s] for n in ns)]
    return np.array(ns), np.array([[curves[s][n] for n in ns] for s in seeds])


def runs_to_target(ns: np.ndarray, scores: np.ndarray) -> np.ndarray:
    out = []
    for row in scores:
        hit = np.nonzero(row >= TARGET)[0]
        out.append(float(ns[hit[0]]) if hit.size else np.inf)
    return np.array(out)


def fmt_iqr(v: np.ndarray) -> str:
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    return f"{med:.2f} ({q1:.2f}–{q3:.2f})"


def fmt_runs(r: np.ndarray) -> tuple[str, str]:
    med = float(np.median(r))
    return ("not reached" if np.isinf(med) else f"{med:g}"), f"{np.mean(np.isfinite(r)):.0%}"


def main(argv: list[str]) -> int:
    path = Path(argv[1])
    data = load(path)
    problems = [p for p in PROBLEM_LABELS if any(k[0] == p for k in data)]
    noises = sorted({k[1] for k in data})

    summary, h2h = [], []
    for p in problems:
        for nz in noises:
            for st in (*SEQUENTIAL, *CLASSICAL, *(f"{m}_best_run" for m in CLASSICAL)):
                if (p, nz, st) not in data:
                    continue
                ns, sc = matrix(data[(p, nz, st)])
                rec = {"problem": p, "noise": nz, "strategy": st, "seeds": len(sc)}
                if st in SEQUENTIAL:
                    for n in (8, 16, 32):
                        idx = np.nonzero(ns == n)[0]
                        rec[f"score_at_{n}"] = fmt_iqr(sc[:, idx[0]]) if idx.size else ""
                    rec["runs_used"] = int(ns[-1])
                else:
                    rec["runs_used"] = int(ns[0])
                    rec["score"] = fmt_iqr(sc[:, 0])
                rt = runs_to_target(ns, sc)
                rec["runs_to_0.95"], rec["seeds_reaching_0.95"] = fmt_runs(rt)
                summary.append(rec)

            # head to head: each classical design vs BO with the same number of runs
            ns_bo, sc_bo = matrix(data[(p, nz, "bo")])
            seeds_bo = sorted(data[(p, nz, "bo")])
            rt_bo = runs_to_target(ns_bo, sc_bo)
            for m in CLASSICAL:
                if (p, nz, m) not in data:
                    continue
                cl = data[(p, nz, m)]
                n_cl = next(iter(next(iter(cl.values()))))
                col = int(np.nonzero(ns_bo >= n_cl)[0][0])
                seeds = [s for s in seeds_bo if s in cl]
                a = np.array([cl[s][n_cl] for s in seeds])
                b = sc_bo[[seeds_bo.index(s) for s in seeds], col]
                diff = b - a
                pval = float(wilcoxon(b, a).pvalue) if np.any(diff) else 1.0
                rt_cl = np.where(a >= TARGET, float(n_cl), np.inf)
                h2h.append(
                    {
                        "problem": p,
                        "noise": nz,
                        "classical": m,
                        "classical_runs": n_cl,
                        "bo_runs": int(ns_bo[col]),
                        "classical_score": fmt_iqr(a),
                        "bo_score": fmt_iqr(b),
                        "median_diff_bo_minus_classical": round(float(np.median(diff)), 3),
                        "bo_better_in_seeds": f"{np.mean(diff > 0):.0%}",
                        "wilcoxon_p": round(pval, 4),
                        "classical_reached_0.95": f"{np.mean(np.isfinite(rt_cl)):.0%}",
                        "bo_runs_to_0.95": fmt_runs(rt_bo)[0],
                        "bo_reached_0.95": fmt_runs(rt_bo)[1],
                    }
                )

    for name, rows in (("e1_summary.csv", summary), ("e1_head_to_head.csv", h2h)):
        keys = list(dict.fromkeys(k for r in rows for k in r))
        with path.with_name(name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, restval="")
            w.writeheader()
            w.writerows(rows)

    md = ["## Head to head (same number of runs)", ""]
    md.append(
        "| Problem | Noise | Classical design | Runs | Classical score | BO score (runs) "
        "| BO − classical (p) | Classical ≥ 0.95 | BO runs to 0.95 (seeds) |"
    )
    md.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in h2h:
        md.append(
            f"| {PROBLEM_LABELS[r['problem']]} | {r['noise']} | {LABELS[r['classical']]} "
            f"| {r['classical_runs']} | {r['classical_score']} | {r['bo_score']} ({r['bo_runs']}) "
            f"| {r['median_diff_bo_minus_classical']:+.2f} (p = {r['wilcoxon_p']:.2g}) "
            f"| {r['classical_reached_0.95']} | {r['bo_runs_to_0.95']} ({r['bo_reached_0.95']}) |"
        )
    md += ["", "## All strategies", ""]
    md.append(
        "| Problem | Noise | Strategy | Runs | Score at 8 | at 16 | at 32 / at its runs "
        "| Runs to 0.95 (median) | Seeds reaching 0.95 |"
    )
    md.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in summary:
        if r["strategy"] in SEQUENTIAL:
            cells = [r["score_at_8"], r["score_at_16"], r["score_at_32"]]
        else:
            cells = ["", "", r["score"]]
        md.append(
            f"| {PROBLEM_LABELS[r['problem']]} | {r['noise']} | {LABELS[r['strategy']]} "
            f"| {r['runs_used']} | " + " | ".join(cells) + f" | {r['runs_to_0.95']} "
            f"| {r['seeds_reaching_0.95']} |"
        )
    path.with_name("e1_summary.md").write_text("\n".join(md) + "\n")

    # ------------------------------------------------------------------ figure
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "text.color": INK})
    fig, axes = plt.subplots(
        len(noises), len(problems), figsize=(3.1 * len(problems), 2.9 * len(noises)), squeeze=False
    )
    for i, nz in enumerate(noises):
        for j, p in enumerate(problems):
            ax = axes[i, j]
            for st in SEQUENTIAL:
                if (p, nz, st) not in data:
                    continue
                ns, sc = matrix(data[(p, nz, st)])
                q1, med, q3 = np.percentile(sc, [25, 50, 75], axis=0)
                dashed = st == "bo_best_run"
                if st != "bo_best_run":
                    ax.fill_between(ns, q1, q3, color=COLORS[st], alpha=0.15, linewidth=0)
                ax.plot(
                    ns,
                    med,
                    color=COLORS[st],
                    linewidth=1.2 if dashed else 2,
                    linestyle="--" if dashed else "-",
                    marker="o" if st == "bo" else None,
                    markersize=3,
                    label=LABELS[st],
                )
            for k, m in enumerate(CLASSICAL):
                if (p, nz, m) not in data:
                    continue
                ns, sc = matrix(data[(p, nz, m)])
                q1, med, q3 = np.percentile(sc[:, 0], [25, 50, 75])
                x = ns[0] + (k - 0.5) * 0.8  # keep BBD and CCD apart when they use equal runs
                ax.errorbar(
                    x,
                    med,
                    yerr=[[med - q1], [q3 - med]],
                    fmt="s",
                    color=COLORS[m],
                    markersize=6,
                    markeredgecolor="white",
                    capsize=2,
                    label=LABELS[m],
                    zorder=5,
                )
            ax.axhline(TARGET, color=MUTED, linewidth=0.8, linestyle=":")
            ax.grid(axis="y", color=GRID, linewidth=0.6)
            ax.set_axisbelow(True)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            ax.tick_params(colors=MUTED)
            ax.set_ylim(-0.3, 1.05)
            n_max = max(n for c in data[(p, nz, "random")].values() for n in c)
            ax.set_xlim(0, n_max + 1)
            if i == 0:
                ax.set_title(PROBLEM_LABELS[p], fontsize=9.5)
            if j == 0:
                ax.set_ylabel(f"Noise {nz}\nscore (1 = optimum)")
            if i == len(noises) - 1:
                ax.set_xlabel("Runs")
    handles, labels = [], []
    for ax in axes.flat:
        for h, lab in zip(*ax.get_legend_handles_labels(), strict=True):
            if lab not in labels:
                handles.append(h)
                labels.append(lab)
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, fontsize=8.5)
    fig.suptitle(
        "E1: Bayesian optimization vs classical response-surface designs (simulated)",
        x=0.01,
        y=0.985,
        ha="left",
        fontsize=11,
    )
    fig.text(
        0.01,
        0.935,
        "Median and IQR over seeds of the true score of the recommended run "
        "(0 = median random run, 1 = optimum). Dotted line: 0.95. "
        "Noise = SD of one measurement / (optimum − median).",
        fontsize=7.5,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.92))
    out_png = path.with_name("e1.png")
    fig.savefig(out_png, dpi=200)
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
