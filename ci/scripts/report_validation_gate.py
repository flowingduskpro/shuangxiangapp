#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report Validation Gate (part of Dependency Integrity Gate).

Purpose
- Validate that the PR evidence tree under `artifacts/` exists and matches the
  fixed naming rules (PR-2 J list).
- Produce machine-auditable results:
  - artifacts/audit/report-validation-result.json
  - artifacts/audit/report-validation-log.txt

Policy source
- `memory_bank/audits/ci-report-validation-rules.md`
- `memory_bank/ShuangxiangApp AI roles.md` section J

Exit codes
- 0: PASS
- 2: FAIL (missing required artifact paths)
- 3: runtime error

Notes
- This validator is intentionally minimal: it checks file existence.
  Future tightening can require non-empty content and JSON schema checks.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_ROOT = REPO_ROOT / "artifacts"
AUDIT_DIR = ARTIFACTS_ROOT / "audit"
RESULT_JSON = AUDIT_DIR / "report-validation-result.json"
LOG_TXT = AUDIT_DIR / "report-validation-log.txt"


# Fixed PR-2 list (J1-J7). Source: memory_bank/audits/ci-report-validation-rules.md
REQUIRED_PATHS = [
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


@dataclass
class ValidationResult:
    ok: bool
    missing: List[str]
    timestamp_utc: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_outputs(result: ValidationResult) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    RESULT_JSON.write_text(
        json.dumps(
            {
                "timestamp_utc": result.timestamp_utc,
                "overall_ok": result.ok,
                "missing": result.missing,
                "required_count": len(REQUIRED_PATHS),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = []
    lines.append(f"timestamp_utc: {result.timestamp_utc}")
    lines.append(f"overall_ok: {str(result.ok).lower()}")
    lines.append(f"required_count: {len(REQUIRED_PATHS)}")
    lines.append(f"missing_count: {len(result.missing)}")
    if result.missing:
        lines.append("missing:")
        lines.extend([f"- {m}" for m in result.missing])
    LOG_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    try:
        missing: List[str] = []
        for rel in REQUIRED_PATHS:
            p = REPO_ROOT / rel
            if not p.exists() or not p.is_file():
                missing.append(rel)

        ok = len(missing) == 0
        result = ValidationResult(ok=ok, missing=missing, timestamp_utc=_utc_now())
        _write_outputs(result)

        if ok:
            print("Report Validation PASSED")
            return 0

        print("Report Validation FAILED:")
        for m in missing:
            print(f"- missing: {m}")
        return 2

    except Exception as e:
        try:
            _write_outputs(
                ValidationResult(ok=False, missing=[f"runtime_error: {e}"], timestamp_utc=_utc_now())
            )
        except Exception:
            pass
        print(f"Report Validation runtime error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

