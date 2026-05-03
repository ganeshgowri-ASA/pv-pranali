"""URS XLSX ingest — prompt 6.1.

Parses iRIL-MxML-FRM-GE-003-Rev00 (or any RIL URS XLSX in docs/urs/source/)
and emits:
  - docs/urs/urs_extracted.yaml   (machine-readable requirements)
  - docs/urs/traceability_matrix.md (req × standard cross-reference)
  - docs/urs/p0_steady_state_simulator.md (human-readable, prepend CONFIDENTIAL)

dry_run=True  (default) — parses and validates but does NOT write files.
dry_run=False — writes output files; requires explicit user authorisation.
"""
from __future__ import annotations

import glob
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SECTION_MAP: dict[str, str] = {
    r"PERF": "Performance",
    r"SAFE": "Safety",
    r"UTIL": "Utility",
    r"WARR": "Warranty",
    r"KPI":  "KPI",
    r"CAL":  "Calibration",
    r"SHIP": "Shipping",
    r"SUPP": "Supplier",
}

CANONICAL_SECTIONS = list(SECTION_MAP.values())

PRIORITY_VALUES = {"Must", "Should", "May"}

SOURCE_DIR = Path("docs/urs/source")
OUTPUT_YAML = Path("docs/urs/urs_extracted.yaml")
OUTPUT_MATRIX = Path("docs/urs/traceability_matrix.md")
OUTPUT_MD = Path("docs/urs/p0_steady_state_simulator.md")


@dataclass
class Requirement:
    id: str
    section: str
    title: str
    priority: str
    text: str
    acceptance_criterion: str
    linked_standard: str
    status: str = "Open"

    def section_from_id(self) -> str:
        prefix = self.id.split("-")[0]
        return SECTION_MAP.get(prefix, "Other")


@dataclass
class UrsIngestResult:
    source_file: Optional[Path]
    requirements: list[Requirement] = field(default_factory=list)
    dry_run: bool = True
    errors: list[str] = field(default_factory=list)

    @property
    def req_count(self) -> int:
        return len(self.requirements)

    @property
    def sections_covered(self) -> set[str]:
        return {r.section for r in self.requirements}

    def is_valid(self) -> bool:
        return len(self.errors) == 0 and self.req_count > 0

    def summary(self) -> str:
        return (
            f"UrsIngestResult(source={self.source_file}, reqs={self.req_count}, "
            f"sections={sorted(self.sections_covered)}, dry_run={self.dry_run}, "
            f"errors={self.errors})"
        )


def _locate_source_xlsx(source_dir: Path = SOURCE_DIR) -> Optional[Path]:
    """Return the most-recently-modified XLSX in source_dir, or None."""
    pattern = str(source_dir / "*.xlsx")
    files = sorted(glob.glob(pattern), key=lambda p: Path(p).stat().st_mtime, reverse=True)
    return Path(files[0]) if files else None


def _parse_xlsx(path: Path) -> list[Requirement]:
    """Parse XLSX and return Requirement list.

    Requires openpyxl. Each sheet is scanned for a column named 'Req-ID'
    (case-insensitive). Rows with a populated Req-ID cell are ingested.
    """
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required for XLSX ingest: pip install openpyxl"
        ) from exc

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    requirements: list[Requirement] = []

    for sheet in wb.worksheets:
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            continue

        header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
        col = {name: idx for idx, name in enumerate(header)}

        req_col = next((k for k in col if "req" in k and "id" in k), None)
        if req_col is None:
            continue

        def _get(row: tuple, key: str, fallback: str = "—") -> str:
            idx = col.get(key)
            if idx is None:
                return fallback
            val = row[idx]
            return str(val).strip() if val is not None else fallback

        for row in rows[1:]:
            req_id = _get(row, req_col, "")
            if not req_id or not re.match(r"[A-Z]+-\d+", req_id):
                continue

            prefix = req_id.split("-")[0]
            section = SECTION_MAP.get(prefix, "Other")

            requirements.append(
                Requirement(
                    id=req_id,
                    section=section,
                    title=_get(row, "title", _get(row, "short title", "—")),
                    priority=_get(row, "priority", "Must"),
                    text=_get(row, "requirement text", _get(row, "text", "—")),
                    acceptance_criterion=_get(
                        row, "acceptance criterion", _get(row, "acceptance criteria", "TBD")
                    ),
                    linked_standard=_get(
                        row, "linked standard", _get(row, "standard", "—")
                    ),
                    status=_get(row, "status", "Open"),
                )
            )

    return requirements


def _load_from_yaml(yaml_path: Path = OUTPUT_YAML) -> list[Requirement]:
    """Fall-back: load requirements from the pre-extracted YAML when no XLSX present."""
    try:
        import yaml  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required: pip install pyyaml"
        ) from exc

    with yaml_path.open() as fh:
        data = yaml.safe_load(fh)

    return [
        Requirement(
            id=r["id"],
            section=r["section"],
            title=r["title"],
            priority=r["priority"],
            text=r.get("text", "—"),
            acceptance_criterion=r.get("acceptance_criterion", "TBD"),
            linked_standard=r.get("linked_standard", "—"),
            status=r.get("status", "Open"),
        )
        for r in data.get("requirements", [])
    ]


def _validate(reqs: list[Requirement]) -> list[str]:
    errors: list[str] = []
    ids_seen: set[str] = set()
    for r in reqs:
        if r.id in ids_seen:
            errors.append(f"Duplicate Req-ID: {r.id}")
        ids_seen.add(r.id)
        if r.section not in CANONICAL_SECTIONS:
            errors.append(f"{r.id}: unknown section '{r.section}'")
        base_priority = r.priority.split(" ")[0]  # handle "Must (LED) / Should (MH)"
        if base_priority not in PRIORITY_VALUES:
            errors.append(f"{r.id}: invalid priority '{r.priority}'")
    return errors


def ingest_urs_xlsx(
    source_dir: Path = SOURCE_DIR,
    dry_run: bool = True,
) -> UrsIngestResult:
    """Main entry point for the 6.1 URS ingest workflow.

    Parameters
    ----------
    source_dir:
        Directory containing the source XLSX file(s). XLSX files are gitignored.
    dry_run:
        When True (default), parse and validate only — no files are written.
        Set to False only after explicit user authorisation.

    Returns
    -------
    UrsIngestResult with parsed requirements and any validation errors.
    """
    source_file = _locate_source_xlsx(source_dir)

    if source_file is not None:
        reqs = _parse_xlsx(source_file)
    else:
        # No XLSX present — fall back to pre-extracted YAML seed
        reqs = _load_from_yaml(OUTPUT_YAML)
        source_file = OUTPUT_YAML  # record what we actually read

    errors = _validate(reqs)
    result = UrsIngestResult(
        source_file=source_file,
        requirements=reqs,
        dry_run=dry_run,
        errors=errors,
    )

    if not dry_run and result.is_valid():
        _write_outputs(result)

    return result


def _write_outputs(result: UrsIngestResult) -> None:
    """Write YAML, traceability matrix, and markdown. Called only when dry_run=False."""
    import yaml  # noqa: PLC0415

    reqs = result.requirements

    # 1. YAML
    OUTPUT_YAML.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "document_ref": "iRIL-MxML-FRM-GE-003-Rev00",
            "customer": "Reliance Industries Ltd, Module R&D Laboratory",
            "instrument": "P0 BBA Steady-State Sun Simulator",
            "dry_run": False,
        },
        "requirements": [
            {
                "id": r.id,
                "section": r.section,
                "title": r.title,
                "priority": r.priority,
                "text": r.text,
                "acceptance_criterion": r.acceptance_criterion,
                "linked_standard": r.linked_standard,
                "status": r.status,
            }
            for r in reqs
        ],
    }
    with OUTPUT_YAML.open("w") as fh:
        yaml.dump(payload, fh, allow_unicode=True, sort_keys=False)

    # 2. Traceability matrix written by separate helper
    _write_traceability_matrix(reqs)

    # 3. Markdown (p0_steady_state_simulator.md) is managed by prompt 6.1 separately


def _write_traceability_matrix(reqs: list[Requirement]) -> None:
    """Write traceability_matrix.md (not called in dry_run mode)."""
    lines = [
        "<!-- CONFIDENTIAL — Reliance Industries Ltd — Not for distribution -->",
        "",
        "# Traceability Matrix — P0 BBA Steady-State Sun Simulator",
        "## URS Reference: iRIL-MxML-FRM-GE-003-Rev00",
        "",
        "| Req-ID | Title | Section | Priority | Linked Standard | Status |",
        "|--------|-------|---------|----------|-----------------|--------|",
    ]
    for r in reqs:
        lines.append(
            f"| {r.id} | {r.title} | {r.section} | {r.priority} "
            f"| {r.linked_standard} | {r.status} |"
        )
    lines += ["", "---", "*Auto-generated by agents/urs/ingest.py*"]
    OUTPUT_MATRIX.write_text("\n".join(lines))
