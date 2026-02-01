#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PR-2 report validation gate.

Validates required artifacts (J1–J7) exist.

Contract:
- Always produces:
  - artifacts/audit/report-validation-result.json
  - artifacts/audit/report-validation-log.txt
- Exit code:
  - 0 on PASS
  - 2 on FAIL (missing files)
  - 3 on unexpected runtime error

Notes:
- This gate checks existence only. Content-level validation is handled by
  dedicated generators (e.g., dependency integrity report generator).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_ROOT = REPO_ROOT / "artifacts"
AUDIT_DIR = ARTIFACTS_ROOT / "audit"
RESULT_JSON = AUDIT_DIR / "report-validation-result.json"
LOG_TXT = AUDIT_DIR / "report-validation-log.txt"

REQUIRED_FILES = [
    # J1
    "artifacts/audit/dependency-integrity-report.md",
    "artifacts/audit/report-validation-result.json",
    "artifacts/audit/report-validation-log.txt",
    # J2
    "artifacts/deps/flutter/pub-resolved.txt",
    "artifacts/deps/flutter/pub-sources.txt",
    "artifacts/deps/flutter/package-resolve-paths.txt",
    "artifacts/deps/node/node-resolved.txt",
    "artifacts/deps/node/node-sources.txt",
    "artifacts/deps/node/node-resolve-paths.txt",
    "artifacts/deps/python/python-deps-status.txt",
    # J3
    "artifacts/security/shadowing-check.txt",
    "artifacts/security/duplicate-module-names.txt",
    # J4
    "artifacts/static/ununsed-imports.txt",
    "artifacts/static/false-integration-check.txt",
    # J5
    "artifacts/tests/flutter-test-report.txt",
    "artifacts/tests/nest-test-report.txt",
    "artifacts/tests/e2e-ws-report.txt",
    # J6
    "artifacts/observability/trace-export.json",
    "artifacts/observability/correlation-ids.txt",
    "artifacts/observability/service-logs.txt",
    "artifacts/observability/e2e-timeline.txt",
    # J7
    "artifacts/runbook/repro-steps.md",
    "artifacts/runbook/versions.txt",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_outputs(*, status: str, missing: list[str], notes: list[str]) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    # log
    lines: list[str] = []
    lines.append(f"timestamp_utc: {_utc_now()}")
    lines.append(f"status: {status}")
    if missing:
        lines.append("missing:")
        for m in missing:
            lines.append(f"- {m}")
    if notes:
        lines.append("notes:")
        for n in notes:
            lines.append(f"- {n}")
    LOG_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # result json
    RESULT_JSON.write_text(
        json.dumps(
            {
                "status": status,
                "timestamp_utc": _utc_now(),
                "missing": missing,
                "notes": notes,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv: list[str]) -> int:
    try:
        missing: list[str] = []
        for rel in REQUIRED_FILES:
            p = REPO_ROOT / rel
            if not p.exists():
                missing.append(rel)

        if missing:
            _write_outputs(
                status="FAIL",
                missing=missing,
                notes=[
                    "Run: python ci/scripts/create_pr_artifacts_skeleton.py to create placeholders.",
                    "Then generate real evidence files and re-run this gate.",
                ],
            )
            print("Report Validation FAILED:")
            for m in missing:
                print(f"- missing: {m}")
            return 2

        _write_outputs(status="PASS", missing=[], notes=["All required PR-2 artifacts exist."])
        print("Report Validation PASSED")
        return 0

    except Exception as e:
        _write_outputs(status="FAIL", missing=[], notes=[f"runtime error: {e}"])
        print(f"Report Validation runtime error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

