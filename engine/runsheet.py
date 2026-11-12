"""Excel run sheet for the lab, and reading the measured results back.

Sheet "Run sheet" layout:
    row 1  human-readable headers (label and unit)
    row 2  machine keys (used when reading back; do not edit)
    row 3+ one row per run, in the order to perform them

Column groups:
    run_order, run_id, std_order, point_type          (filled in, grey)
    <factor>              planned value                (filled in, grey)
    <factor>__applied     value actually used, only if different from planned
    <response>            measured value
    <record columns>      extra observations, e.g. bath temperature
    notes                 free text

When reading back, a run counts as measured once every response cell holds a
number. If an "applied" cell is filled, that value replaces the planned one,
so the model always sees the condition that was really used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from engine.config import ExperimentConfig
from engine.interface import Run

APPLIED = "__applied"
META = ["run_order", "run_id", "std_order", "point_type"]
META_LABELS = {
    "run_order": "Run order",
    "run_id": "Run ID",
    "std_order": "Std order",
    "point_type": "Point type",
}
GREY = PatternFill("solid", fgColor="F1F5F9")
INPUT = PatternFill("solid", fgColor="EEF7F6")
HEAD = Font(bold=True, color="1F3A5F")
KEY = Font(size=8, color="94A3B8")


def _columns(cfg: ExperimentConfig) -> list[tuple[str, str, bool]]:
    """(key, header label, is_input) for every column, left to right."""
    cols = [(k, META_LABELS[k], False) for k in META]
    for f in cfg.factors:
        unit = f" ({f.unit})" if f.unit else ""
        cols.append((f.name, f"{f.label}{unit}", False))
    for f in cfg.factors:
        unit = f" ({f.unit})" if f.unit else ""
        cols.append((f.name + APPLIED, f"{f.label} applied{unit}, only if different", True))
    for r in cfg.responses:
        unit = f" ({r.unit})" if r.unit else ""
        cols.append((r.name, f"{r.name} measured{unit}", True))
    cols += [(c, c, True) for c in cfg.record_columns]
    cols.append(("notes", "Notes", True))
    return cols


def write_run_sheet(cfg: ExperimentConfig, runs: list[Run], path: str | Path, method: str) -> Path:
    path = Path(path)
    wb = Workbook()
    ws = wb.active
    ws.title = "Run sheet"
    cols = _columns(cfg)
    for j, (key, label, is_input) in enumerate(cols, start=1):
        h = ws.cell(row=1, column=j, value=label)
        h.font = HEAD
        h.alignment = Alignment(wrap_text=True, vertical="top", horizontal="center")
        ws.cell(row=2, column=j, value=key).font = KEY
        ws.column_dimensions[get_column_letter(j)].width = 10 if key in META else 16
        for i, run in enumerate(runs, start=3):
            c = ws.cell(row=i, column=j, value=None if is_input else run.get(key))
            c.fill = INPUT if is_input else GREY
            c.alignment = Alignment(horizontal="center")
    ws.row_dimensions[1].height = 62
    ws.freeze_panes = "C3"
    # Printed at the bench: landscape, all columns on one page width, headers repeated.
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "1:2"
    ws.print_options.gridLines = True

    info = wb.create_sheet("Info")
    lines = [
        ("Experiment", cfg.name),
        ("Design", method),
        ("Runs", len(runs)),
        ("Random seed (run order)", cfg.spec.seed),
        ("Created", date.today().isoformat()),
        ("", ""),
        ("How to fill in", ""),
        ("1", "Perform the runs in 'Run order' (top to bottom)."),
        ("2", "Write each measured response as a number in its column."),
        (
            "3",
            "If a condition was applied differently, write the real value in its 'applied' "
            "column. Leave it empty if the run was done as planned.",
        ),
        ("4", "Do not change rows 1-2, the grey cells, or the order of the columns."),
        ("", ""),
        ("Factor", "Label | unit | low | high"),
    ]
    for f, p in zip(cfg.factors, cfg.spec.parameters, strict=True):
        lo, hi = p.bounds
        lines.append((f.name, f"{f.label} | {f.unit} | {lo:g} | {hi:g}"))
    for i, (a, b) in enumerate(lines, start=1):
        info.cell(row=i, column=1, value=a).font = Font(bold=True)
        info.cell(row=i, column=2, value=b)
    info.column_dimensions["A"].width = 24
    info.column_dimensions["B"].width = 90

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def _number(v: object) -> float | None:
    """Cell value -> float. Accepts '1,23' (Turkish decimal comma). Empty -> None."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, bool):
        raise ValueError(f"not a number: {v!r}")
    if isinstance(v, int | float):
        return float(v)
    return float(str(v).strip().replace(",", "."))


@dataclass
class SheetResults:
    measured: list[Run] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)  # run_ids not (fully) measured yet
    problems: list[str] = field(default_factory=list)  # anything a person should look at


def read_results(cfg: ExperimentConfig, path: str | Path) -> SheetResults:
    ws = load_workbook(Path(path), data_only=True)["Run sheet"]
    keys = [c.value for c in ws[2]]
    expected = [k for k, _, _ in _columns(cfg)]
    missing = [k for k in expected if k not in keys]
    if missing:
        raise ValueError(f"run sheet is missing columns {missing}; was row 2 edited?")
    col = {k: keys.index(k) for k in expected}
    bounds = {p.name: p.bounds for p in cfg.spec.parameters}

    out = SheetResults()
    for row in ws.iter_rows(min_row=3, values_only=True):
        if all(v is None for v in row):
            continue
        rid = str(row[col["run_id"]])
        try:
            resp = {r.name: _number(row[col[r.name]]) for r in cfg.responses}
        except ValueError as e:
            out.problems.append(f"{rid}: response is not a number ({e})")
            out.pending.append(rid)
            continue
        if any(v is None for v in resp.values()):
            out.pending.append(rid)
            continue
        run: Run = {k: row[col[k]] for k in META}
        for f in cfg.factors:
            planned = _number(row[col[f.name]])
            try:
                applied = _number(row[col[f.name + APPLIED]])
            except ValueError as e:
                out.problems.append(f"{rid}: applied {f.name} is not a number ({e}); used planned")
                applied = None
            value = planned if applied is None else applied
            lo, hi = bounds[f.name]
            if not lo <= value <= hi:
                out.problems.append(f"{rid}: {f.name} = {value:g} is outside {lo:g}-{hi:g}")
            run[f.name] = value
        run.update(resp)
        for c in cfg.record_columns:
            if row[col[c]] is not None:
                run[c] = row[col[c]]
        if row[col["notes"]]:
            run["notes"] = str(row[col["notes"]])
        out.measured.append(run)
    return out
