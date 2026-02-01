#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Observability Gate (minimal/token-only).

This is the original Gate 6 behavior kept for early-phase CI workflows.
It validates:
- artifacts/observability/service-logs.txt contains `x-correlation-id` and `correlation_id`
- artifacts/observability/correlation-ids.txt exists
- at least one business field token exists (default: `class_session_id`)

The strict PR-2 requirement (real trace chain in trace-export.json) is validated
in the dedicated workflow `.github/workflows/pr2-e2e.yml` using
`ci/scripts/observability_gate.py`.

Contract:
- Always produces: ci_artifacts/trace-evidence.md
- Exit code 0 on PASS/N/A, 2 on FAIL, 3 on runtime error.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "ci_artifacts"
TRACE_EVIDENCE_PATH = ARTIFACTS_DIR / "trace-evidence.md"

PR2_OBS_DIR = REPO_ROOT / "artifacts" / "observability"
PR2_SERVICE_LOGS = PR2_OBS_DIR / "service-logs.txt"
PR2_CORRELATION_IDS = PR2_OBS_DIR / "correlation-ids.txt"

CORRELATION_HEADER = "x-correlation-id"
CORRELATION_FIELD = "correlation_id"
DEFAULT_BUSINESS_FIELDS = ["class_session_id"]


@dataclass
class CheckResult:
    name: str
    ok: bool
    conclusion: str  # PASS/FAIL/N/A
    evidence: str
    risk: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iter_files_by_name(name: str) -> List[Path]:
    exclude_dirs = {
        ".git",
        ".idea",
        "ci_artifacts",
        "node_modules",
        "build",
        "dist",
        "generated",
        ".dart_tool",
        ".venv",
        "__pycache__",
    }
    hits: List[Path] = []
    for p in REPO_ROOT.rglob(name):
        parts = {x.lower() for x in p.parts}
        if any(ed.lower() in parts for ed in exclude_dirs):
            continue
        if p.is_file() and p.name == name:
            hits.append(p)
    return sorted(hits, key=lambda x: x.relative_to(REPO_ROOT).as_posix())


def _has_any_manifest() -> bool:
    return any(
        _iter_files_by_name(n)
        for n in ("pubspec.yaml", "package.json", "requirements.txt", "pyproject.toml")
    )


def _write_evidence(*, checks: List[CheckResult], overall_ok: bool) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append("# trace-evidence.md")
    lines.append("")
    lines.append("This file is produced by Gate 6 (Observability Gate) automation.")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- timestamp_utc: `{_utc_now()}`")
    lines.append("")
    lines.append("## Policy")
    lines.append("- Minimal token-only check (legacy)")
    lines.append(f"- Required correlation header: `{CORRELATION_HEADER}`")
    lines.append(f"- Required log field: `{CORRELATION_FIELD}`")
    lines.append(f"- Required business fields (at least one): {', '.join('`'+x+'`' for x in DEFAULT_BUSINESS_FIELDS)}")
    lines.append("")
    lines.append("## Checks")
    for c in checks:
        lines.append(f"### {c.name}: {c.conclusion}")
        lines.append("")
        lines.append(f"- ok: `{str(c.ok).lower()}`")
        lines.append(f"- evidence: {c.evidence}")
        lines.append(f"- risk: {c.risk}")
        lines.append("")
    lines.append("## Overall")
    lines.append(f"- overall_ok: `{str(overall_ok).lower()}`")
    lines.append("")

    TRACE_EVIDENCE_PATH.write_text("\n".join(lines), encoding="utf-8")


def _check_minimal_evidence() -> CheckResult:
    if not _has_any_manifest():
        return CheckResult(
            name="Minimal E2E observability evidence",
            ok=True,
            conclusion="N/A",
            evidence="repo scan found no manifests; docs-only phase",
            risk="N/A",
        )

    if not PR2_OBS_DIR.exists():
        return CheckResult(
            name="Minimal E2E observability evidence",
            ok=False,
            conclusion="FAIL",
            evidence=f"Missing required observability dir: `{PR2_OBS_DIR.relative_to(REPO_ROOT).as_posix()}`",
            risk="Without artifacts/observability, MVP trace/log correlation can't be audited",
        )

    if not PR2_SERVICE_LOGS.exists() or not PR2_CORRELATION_IDS.exists():
        missing = []
        if not PR2_SERVICE_LOGS.exists():
            missing.append(PR2_SERVICE_LOGS.relative_to(REPO_ROOT).as_posix())
        if not PR2_CORRELATION_IDS.exists():
            missing.append(PR2_CORRELATION_IDS.relative_to(REPO_ROOT).as_posix())
        return CheckResult(
            name="Minimal E2E observability evidence",
            ok=False,
            conclusion="FAIL",
            evidence="Missing required PR-2 evidence files: " + ", ".join(missing),
            risk="Without these files, correlation ids and service logs for the MVP chain can't be audited",
        )

    text = (
        PR2_SERVICE_LOGS.read_text(encoding="utf-8", errors="replace")
        + "\n"
        + PR2_CORRELATION_IDS.read_text(encoding="utf-8", errors="replace")
    )

    missing: List[str] = []
    if CORRELATION_HEADER not in text:
        missing.append(CORRELATION_HEADER)
    if CORRELATION_FIELD not in text:
        missing.append(CORRELATION_FIELD)
    if not any(bf in text for bf in DEFAULT_BUSINESS_FIELDS):
        missing.append("one of: " + ", ".join(DEFAULT_BUSINESS_FIELDS))

    if not missing:
        return CheckResult(
            name="Minimal E2E observability evidence",
            ok=True,
            conclusion="PASS",
            evidence="artifacts/observability contains required correlation keys and at least one business field",
            risk="N/A",
        )

    return CheckResult(
        name="Minimal E2E observability evidence",
        ok=False,
        conclusion="FAIL",
        evidence="observability evidence missing tokens: " + ", ".join(missing),
        risk="Without these keys, correlation across logs/traces/DB events won't be verifiable",
    )


def main(argv: Sequence[str]) -> int:
    try:
        checks = [_check_minimal_evidence()]
        overall_ok = all(c.ok for c in checks)
        _write_evidence(checks=checks, overall_ok=overall_ok)

        if overall_ok:
            print("Observability Gate (minimal) PASSED")
            print(f"Evidence written: {TRACE_EVIDENCE_PATH}")
            return 0

        print("Observability Gate (minimal) FAILED:", file=sys.stderr)
        for c in checks:
            if not c.ok:
                print(f"- {c.name}: {c.evidence}", file=sys.stderr)
        print(f"\nSee evidence: {TRACE_EVIDENCE_PATH}", file=sys.stderr)
        return 2

    except Exception as e:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            _write_evidence(
                checks=[
                    CheckResult(
                        name="runtime",
                        ok=False,
                        conclusion="FAIL",
                        evidence=str(e),
                        risk="Gate runtime error; observability evidence may be missing",
                    )
                ],
                overall_ok=False,
            )
        except Exception:
            pass

        print(f"Observability Gate (minimal) runtime error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

