"""Concentration vs yield in the Çimyapan (2024) extraction data.

Top row: soluble protein (g/L) against biomass concentration, one panel per
species. Bottom row: the same runs as yield (mg protein per g biomass). Colour
encodes extraction time (one hue, light = short, dark = long). The run flagged
`suspect_value` is drawn hollow and labelled; it is not used in any summary.

Usage: python scripts/plot_cimyapan2024.py
Needs matplotlib (see requirements-engine.txt). Run build_cimyapan2024.py first.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, Normalize  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "public" / "cimyapan2024"
OUT = DATA / "yield_vs_biomass.png"

SPECIES = [
    ("S_platensis", "S. platensis"),
    ("A_protothecoides", "A. protothecoides"),
    ("S_limacinum", "S. limacinum"),
]
INK, MUTED, GRID, WINE = "#1E293B", "#64748B", "#E2E8F0", "#9F1239"
TIME_CMAP = LinearSegmentedColormap.from_list("time", ["#9CC3EC", "#2a78d6", "#0E2F57"])


def load() -> list[dict[str, str]]:
    with (DATA / "extraction_runs.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    rows = load()
    norm = Normalize(vmin=0, vmax=50)
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "text.color": INK})
    fig, axes = plt.subplots(2, 3, figsize=(10, 6.2), sharex=True, sharey="row")
    rows_spec = [
        ("soluble_protein_g_L", "Soluble protein (g/L)"),
        ("yield_mg_per_g", "Yield (mg protein / g biomass)"),
    ]
    for r, (col, ylabel) in enumerate(rows_spec):
        for c, (sp, title) in enumerate(SPECIES):
            ax = axes[r, c]
            sub = [d for d in rows if d["species"] == sp]
            ok = [d for d in sub if d["use_in_model"] == "1"]
            bad = [d for d in sub if d["use_in_model"] == "0"]
            ax.scatter(
                [float(d["biomass_g_L"]) for d in ok],
                [float(d[col]) for d in ok],
                c=[float(d["time_min"]) for d in ok],
                cmap=TIME_CMAP,
                norm=norm,
                s=46,
                edgecolors="white",
                linewidths=1.5,
                zorder=3,
            )
            for d in bad:
                x, y = float(d["biomass_g_L"]), float(d[col])
                ax.scatter(x, y, s=46, facecolors="none", edgecolors=WINE, linewidths=1.4, zorder=3)
                ax.annotate(
                    "suspect value\n(excluded)",
                    (x, y),
                    xytext=(-9, -2),
                    textcoords="offset points",
                    ha="right",
                    va="center",
                    fontsize=7.5,
                    color=MUTED,
                )
            ax.grid(color=GRID, linewidth=0.6)
            ax.set_axisbelow(True)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
            if r == 0:
                ax.set_title(title, fontsize=10, fontstyle="italic", color=INK)
            if c == 0:
                ax.set_ylabel(ylabel, color=INK)
            if r == 1:
                ax.set_xlabel("Biomass concentration (g/L)", color=INK)
            ax.tick_params(colors=MUTED)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=TIME_CMAP)
    cb = fig.colorbar(sm, ax=axes, shrink=0.6, pad=0.02)
    cb.set_label("Extraction time (min)", color=INK)
    cb.outline.set_visible(False)
    fig.suptitle(
        "Çimyapan (2024): soluble protein rises with biomass, yield per gram does not",
        x=0.02,
        ha="left",
        fontsize=11,
        color=INK,
    )
    fig.text(
        0.02,
        0.005,
        "Source: Çimyapan (2024), GTU MSc thesis, Tables 3.1–3.3. Probe ultrasound "
        "(Bandelin HD 2070), Lowry assay. Yield = protein (g/L) / biomass (g/L).",
        fontsize=7.5,
        color=MUTED,
    )
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
