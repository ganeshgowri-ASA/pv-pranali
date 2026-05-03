"""Unit tests for agents/urs/ingest.py — prompt 6.1 URS ingest.

All tests run in dry_run=True mode (no files written, no live API calls).
The XLSX source is gitignored; tests fall back to the pre-extracted YAML seed.
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.urs.ingest import (
    CANONICAL_SECTIONS,
    PRIORITY_VALUES,
    Requirement,
    UrsIngestResult,
    _load_from_yaml,
    _validate,
    ingest_urs_xlsx,
)


YAML_SEED = Path("docs/urs/urs_extracted.yaml")
MATRIX_PATH = Path("docs/urs/traceability_matrix.md")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_req(**kwargs) -> Requirement:
    defaults = dict(
        id="PERF-001",
        section="Performance",
        title="Irradiance Range",
        priority="Must",
        text="The simulator shall provide 700–1300 W/m².",
        acceptance_criterion="Within ±2% of setpoint.",
        linked_standard="IEC 60904-9:2020 §5.3",
        status="Open",
    )
    defaults.update(kwargs)
    return Requirement(**defaults)


# ---------------------------------------------------------------------------
# UrsIngestResult
# ---------------------------------------------------------------------------

class TestUrsIngestResult:
    def test_req_count(self):
        result = UrsIngestResult(source_file=None, requirements=[_make_req()])
        assert result.req_count == 1

    def test_sections_covered(self):
        reqs = [_make_req(section="Performance"), _make_req(id="SAFE-001", section="Safety")]
        result = UrsIngestResult(source_file=None, requirements=reqs)
        assert "Performance" in result.sections_covered
        assert "Safety" in result.sections_covered

    def test_is_valid_with_no_errors(self):
        result = UrsIngestResult(source_file=None, requirements=[_make_req()], errors=[])
        assert result.is_valid()

    def test_is_invalid_with_errors(self):
        result = UrsIngestResult(
            source_file=None, requirements=[_make_req()], errors=["bad section"]
        )
        assert not result.is_valid()

    def test_is_invalid_when_empty(self):
        result = UrsIngestResult(source_file=None, requirements=[], errors=[])
        assert not result.is_valid()

    def test_dry_run_defaults_true(self):
        result = UrsIngestResult(source_file=None)
        assert result.dry_run is True

    def test_summary_contains_key_fields(self):
        result = UrsIngestResult(
            source_file=Path("some.xlsx"),
            requirements=[_make_req()],
            dry_run=True,
        )
        s = result.summary()
        assert "dry_run=True" in s
        assert "reqs=1" in s


# ---------------------------------------------------------------------------
# _validate
# ---------------------------------------------------------------------------

class TestValidate:
    def test_valid_requirements_produce_no_errors(self):
        reqs = [_make_req(id=f"PERF-{i:03d}") for i in range(1, 5)]
        assert _validate(reqs) == []

    def test_duplicate_id_flagged(self):
        reqs = [_make_req(id="PERF-001"), _make_req(id="PERF-001")]
        errors = _validate(reqs)
        assert any("Duplicate" in e for e in errors)

    def test_unknown_section_flagged(self):
        reqs = [_make_req(section="Bogus")]
        errors = _validate(reqs)
        assert any("unknown section" in e for e in errors)

    def test_invalid_priority_flagged(self):
        reqs = [_make_req(priority="Critical")]
        errors = _validate(reqs)
        assert any("invalid priority" in e for e in errors)

    def test_priority_with_variant_annotation_accepted(self):
        # e.g. "Must (LED variant) / Should (MH variant)"
        reqs = [_make_req(priority="Must (LED variant) / Should (MH variant)")]
        errors = _validate(reqs)
        assert errors == []

    def test_all_canonical_sections_accepted(self):
        reqs = [
            _make_req(id=f"{s[:4].upper()}-001", section=s)
            for s in CANONICAL_SECTIONS
        ]
        assert _validate(reqs) == []

    def test_all_priority_values_accepted(self):
        reqs = [
            _make_req(id=f"PERF-{i:03d}", priority=p)
            for i, p in enumerate(sorted(PRIORITY_VALUES), 1)
        ]
        assert _validate(reqs) == []


# ---------------------------------------------------------------------------
# _load_from_yaml (seed fallback)
# ---------------------------------------------------------------------------

class TestLoadFromYaml:
    def test_yaml_seed_loads(self):
        if not YAML_SEED.exists():
            pytest.skip("YAML seed not present")
        reqs = _load_from_yaml(YAML_SEED)
        assert len(reqs) >= 23

    def test_yaml_seed_has_all_sections(self):
        if not YAML_SEED.exists():
            pytest.skip("YAML seed not present")
        reqs = _load_from_yaml(YAML_SEED)
        sections = {r.section for r in reqs}
        for s in CANONICAL_SECTIONS:
            assert s in sections, f"Section '{s}' missing from YAML seed"

    def test_yaml_seed_req_ids_unique(self):
        if not YAML_SEED.exists():
            pytest.skip("YAML seed not present")
        reqs = _load_from_yaml(YAML_SEED)
        ids = [r.id for r in reqs]
        assert len(ids) == len(set(ids)), "Duplicate Req-IDs in YAML seed"

    def test_yaml_seed_validates_clean(self):
        if not YAML_SEED.exists():
            pytest.skip("YAML seed not present")
        reqs = _load_from_yaml(YAML_SEED)
        errors = _validate(reqs)
        assert errors == [], f"Validation errors in YAML seed: {errors}"


# ---------------------------------------------------------------------------
# ingest_urs_xlsx (integration, dry_run=True)
# ---------------------------------------------------------------------------

class TestIngestUrsDryRun:
    def test_returns_result_object(self, tmp_path):
        result = ingest_urs_xlsx(source_dir=tmp_path, dry_run=True)
        assert isinstance(result, UrsIngestResult)

    def test_dry_run_flag_preserved(self, tmp_path):
        result = ingest_urs_xlsx(source_dir=tmp_path, dry_run=True)
        assert result.dry_run is True

    def test_no_xlsx_falls_back_to_yaml(self, tmp_path):
        # tmp_path has no XLSX → fall back to YAML seed
        if not YAML_SEED.exists():
            pytest.skip("YAML seed not present")
        result = ingest_urs_xlsx(source_dir=tmp_path, dry_run=True)
        assert result.req_count >= 23

    def test_does_not_write_files_in_dry_run(self, tmp_path):
        """dry_run=True must never write output files."""
        if not YAML_SEED.exists():
            pytest.skip("YAML seed not present")
        before = list(Path("docs/urs").glob("*.yaml")) + list(Path("docs/urs").glob("*.md"))
        ingest_urs_xlsx(source_dir=tmp_path, dry_run=True)
        after = list(Path("docs/urs").glob("*.yaml")) + list(Path("docs/urs").glob("*.md"))
        # file list should not grow
        assert set(str(p) for p in after) == set(str(p) for p in before)

    def test_result_is_valid_with_yaml_seed(self, tmp_path):
        if not YAML_SEED.exists():
            pytest.skip("YAML seed not present")
        result = ingest_urs_xlsx(source_dir=tmp_path, dry_run=True)
        assert result.is_valid()

    def test_performance_requirements_present(self, tmp_path):
        if not YAML_SEED.exists():
            pytest.skip("YAML seed not present")
        result = ingest_urs_xlsx(source_dir=tmp_path, dry_run=True)
        perf_ids = {r.id for r in result.requirements if r.section == "Performance"}
        expected = {"PERF-001", "PERF-002", "PERF-003", "PERF-004", "PERF-005", "PERF-006", "PERF-007"}
        assert expected.issubset(perf_ids)

    def test_bba_parameters_covered(self, tmp_path):
        """Key BBA parameters (irradiance range, temp, 4-wire, classification) are present."""
        if not YAML_SEED.exists():
            pytest.skip("YAML seed not present")
        result = ingest_urs_xlsx(source_dir=tmp_path, dry_run=True)
        req_map = {r.id: r for r in result.requirements}

        # Irradiance 700–1300 W/m²
        assert "700" in req_map["PERF-001"].text or "700" in req_map["PERF-001"].acceptance_criterion

        # Temperature 20–75 °C
        assert "20" in req_map["PERF-006"].text

        # 4-wire I-V
        assert "4-wire" in req_map["PERF-007"].text.lower() or "kelvin" in req_map["PERF-007"].text.lower()

        # ISO 17025 calibration
        cal_standards = req_map["CAL-001"].linked_standard
        assert "17025" in cal_standards

    def test_xlsx_parse_called_when_file_present(self, tmp_path):
        """When an XLSX is present, _parse_xlsx should be invoked."""
        fake_xlsx = tmp_path / "iRIL-MxML-FRM-GE-003-Rev00.xlsx"
        fake_xlsx.touch()

        mock_reqs = [_make_req()]
        with patch("agents.urs.ingest._parse_xlsx", return_value=mock_reqs) as mock_parse:
            result = ingest_urs_xlsx(source_dir=tmp_path, dry_run=True)

        mock_parse.assert_called_once_with(fake_xlsx)
        assert result.req_count == 1


# ---------------------------------------------------------------------------
# Traceability matrix artifact
# ---------------------------------------------------------------------------

class TestTraceabilityMatrix:
    def test_matrix_file_exists(self):
        assert MATRIX_PATH.exists(), "traceability_matrix.md not found"

    def test_matrix_has_all_req_ids(self):
        if not MATRIX_PATH.exists():
            pytest.skip("Matrix file not present")
        content = MATRIX_PATH.read_text()
        expected_ids = [
            "PERF-001", "PERF-007", "SAFE-001", "SAFE-004",
            "UTIL-001", "WARR-001", "KPI-001", "CAL-001", "SHIP-001", "SUPP-001",
        ]
        for rid in expected_ids:
            assert rid in content, f"{rid} missing from traceability matrix"

    def test_matrix_is_confidential(self):
        if not MATRIX_PATH.exists():
            pytest.skip("Matrix file not present")
        content = MATRIX_PATH.read_text()
        assert "CONFIDENTIAL" in content

    def test_matrix_has_standards_summary(self):
        if not MATRIX_PATH.exists():
            pytest.skip("Matrix file not present")
        content = MATRIX_PATH.read_text()
        assert "IEC 60904-9" in content
        assert "ISO/IEC 17025" in content
