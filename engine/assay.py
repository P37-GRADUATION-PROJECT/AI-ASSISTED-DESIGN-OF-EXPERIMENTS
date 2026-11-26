"""Turn assay readings into a response value: the Lowry protein assay.

The institute measures soluble protein with the Lowry method (LabBio Food
instruction LBF3): each sample is diluted (e.g. 10x: 50 uL sample + 450 uL
water), read twice at 750 nm, and converted with a BSA calibration line

    absorbance = slope * concentration + intercept     (concentration in mg/mL)

so the sample's concentration is

    protein = (mean absorbance - intercept) / slope * dilution    (mg/mL = g/L)

This is exactly the formula in the lab's own Excel sheet. Doing it here
means the lab types only what the instrument shows (the absorbances and the
dilution), and the same calculation is applied to every run.

Quality flags (from the instruction and the first lab batch, 25 Nov 2026):

- mean absorbance below ``abs_min`` (0.100 in LBF3 note 10.2): the sample was
  probably diluted too much; the intercept then dominates the result.
- mean absorbance above ``abs_max``: outside the calibration range; dilute more.
- the replicate readings differ by more than ``max_rel_diff`` of their mean.

A flagged run is still used; the flag is reported so a person can decide.
"""

from __future__ import annotations

from dataclasses import dataclass

ASSAY_METHODS = ("lowry",)


@dataclass(frozen=True)
class AssaySettings:
    """Calibration and checks for one measured response (config ``[assay.<response>]``)."""

    method: str
    slope: float  # absorbance per (mg/mL) of standard
    intercept: float  # absorbance at zero concentration (from the calibration fit)
    dilution: float = 1.0  # default dilution factor written on the run sheet
    replicates: int = 2  # absorbance readings per sample
    abs_min: float = 0.100
    abs_max: float = 1.000
    max_rel_diff: float = 0.15
    reference: str = ""  # where the calibration comes from (instruction, date of standards)

    def __post_init__(self) -> None:
        if self.method not in ASSAY_METHODS:
            raise ValueError(f"assay method must be one of {ASSAY_METHODS}, got {self.method!r}")
        if self.slope <= 0:
            raise ValueError("assay slope must be positive")
        if self.dilution < 1:
            raise ValueError("assay dilution factor must be at least 1")
        if self.replicates < 1:
            raise ValueError("assay replicates must be at least 1")
        if not 0 <= self.abs_min < self.abs_max:
            raise ValueError("assay needs 0 <= abs_min < abs_max")
        if self.max_rel_diff <= 0:
            raise ValueError("assay max_rel_diff must be positive")


@dataclass(frozen=True)
class AssayResult:
    value: float  # g/L (mg/mL) in the undiluted sample
    mean_absorbance: float
    flags: tuple[str, ...]


def lowry(readings: list[float], dilution: float, cal: AssaySettings) -> AssayResult:
    """Protein concentration (g/L) of the undiluted sample from its absorbance readings."""
    if not readings:
        raise ValueError("no absorbance readings")
    if dilution < 1:
        raise ValueError(f"dilution factor must be at least 1, got {dilution:g}")
    mean = sum(readings) / len(readings)
    value = (mean - cal.intercept) / cal.slope * dilution
    flags = []
    if mean < cal.abs_min:
        flags.append(
            f"absorbance {mean:.3f} is below {cal.abs_min:g}: probably diluted too much, "
            "the result is uncertain"
        )
    if mean > cal.abs_max:
        flags.append(
            f"absorbance {mean:.3f} is above {cal.abs_max:g}: outside the calibration range, "
            "dilute more and measure again"
        )
    if len(readings) > 1 and mean > 0:
        spread = (max(readings) - min(readings)) / mean
        if spread > cal.max_rel_diff:
            flags.append(
                f"replicate readings differ by {spread:.0%} of their mean "
                f"(limit {cal.max_rel_diff:.0%})"
            )
    if value < 0:
        flags.append("negative concentration: absorbance is below the calibration intercept")
    return AssayResult(value=value, mean_absorbance=mean, flags=tuple(flags))


def parse_assay(name: str, a: dict) -> AssaySettings:
    where = f"assay.{name}"
    for key in ("method", "slope", "intercept"):
        if key not in a:
            raise ValueError(f"{where}: missing required key {key!r}")
    known = set(AssaySettings.__dataclass_fields__)
    unknown = set(a) - known
    if unknown:
        raise ValueError(f"{where}: unknown keys {sorted(unknown)}")
    return AssaySettings(
        method=str(a["method"]),
        slope=float(a["slope"]),
        intercept=float(a["intercept"]),
        dilution=float(a.get("dilution", 1.0)),
        replicates=int(a.get("replicates", 2)),
        abs_min=float(a.get("abs_min", 0.100)),
        abs_max=float(a.get("abs_max", 1.000)),
        max_rel_diff=float(a.get("max_rel_diff", 0.15)),
        reference=str(a.get("reference", "")),
    )
