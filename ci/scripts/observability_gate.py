#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Observability Gate (Gate 6) checker.

Implements rules from `memory_bank/implementation-plan.md` section 6.

Goal (MVP): every PR must produce minimal, auditable observability evidence for
at least one end-to-end chain described in section 0.6.

Because this repo can be in a docs-only phase, the gate supports N/A and PASS
when no runnable code/manifests exist yet. However, it always produces an
artifact file at `ci_artifacts/trace-evidence.md`.

Contract:
- Always produce: `ci_artifacts/trace-evidence.md`
- Exit code:
  - 0 on pass (including N/A)
  - 2 on fail (rule violations)
  - 3 on unexpected runtime error

Minimal machine-checkable rules (current):
- If no repo manifests exist (pubspec.yaml / package.json / requirements.txt / pyproject.toml):
  - Evidence is marked as N/A and gate PASS.
- Otherwise (code exists): require evidence file to contain, at minimum:
  - a correlation id header key: `x-correlation-id`
  - the log field name: `correlation_id`
  - at least one business key field name (default: `class_session_id`)

Notes:
- This gate does not start services or run smoke tests in this repo state.
  Later iterations can tighten this by generating evidence from a deterministic
  smoke script and by validating traces/logs/DB entries end-to-end.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "ci_artifacts"
TRACE_EVIDENCE_PATH = ARTIFACTS_DIR / "trace-evidence.md"

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
    lines.append("- Source: `memory_bank/implementation-plan.md` section 6")
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
            evidence=(
                "repo scan found no manifests (pubspec.yaml/package.json/requirements.txt/pyproject.toml); "
                "treating as docs-only phase"
            ),
            risk="N/A",
        )

    # If code exists, require evidence file to already exist and contain required tokens.
    if not TRACE_EVIDENCE_PATH.exists():
        return CheckResult(
            name="Minimal E2E observability evidence",
            ok=False,
            conclusion="FAIL",
            evidence=f"Missing required artifact: `{TRACE_EVIDENCE_PATH.relative_to(REPO_ROOT).as_posix()}`",
            risk="Without evidence, trace/log correlation for the MVP chain can't be audited",
        )

    text = TRACE_EVIDENCE_PATH.read_text(encoding="utf-8", errors="replace")
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
            evidence="trace-evidence.md contains required correlation keys and at least one business field",
            risk="N/A",
        )

    return CheckResult(
        name="Minimal E2E observability evidence",
        ok=False,
        conclusion="FAIL",
        evidence="trace-evidence.md missing tokens: " + ", ".join(missing),
        risk="Without these keys, correlation across logs/traces/DB events won't be verifiable",
    )


def main(argv: Sequence[str]) -> int:
    try:
        # Always (re)write evidence with current check results.
        # If code exists, we validate existing evidence content; if docs-only, we emit N/A evidence.
        checks = [_check_minimal_evidence()]
        overall_ok = all(c.ok for c in checks)
        _write_evidence(checks=checks, overall_ok=overall_ok)

        if overall_ok:
            print("Observability Gate PASSED")
            print(f"Evidence written: {TRACE_EVIDENCE_PATH}")
            return 0

        print("Observability Gate FAILED:", file=sys.stderr)
        for c in checks:
            if not c.ok:
                print(f"- {c.name}: {c.evidence}", file=sys.stderr)
        print(f"\nSee evidence: {TRACE_EVIDENCE_PATH}", file=sys.stderr)
        return 2

    except Exception as e:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        # Best-effort error evidence.
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

        print(f"Observability Gate runtime error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

