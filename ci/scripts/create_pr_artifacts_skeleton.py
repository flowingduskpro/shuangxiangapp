#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PR-2 artifacts skeleton creator.

Always produces the fixed artifacts directory/file list required by
`memory_bank/ShuangxiangApp AI roles.md` section J (J1–J7).

Contract:
- Create directories and placeholder files if missing.
- Never delete existing evidence files.
- Exit code 0 always unless unexpected runtime error.

Why this exists:
- CI must fail if any required artifact is missing. The validation gate checks
  for existence; this script ensures a deterministic baseline.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_ROOT = REPO_ROOT / "artifacts"

REQUIRED_FILES = [
    # J1
    "audit/dependency-integrity-report.md",
    "audit/report-validation-result.json",
    "audit/report-validation-log.txt",
    # J2
    "deps/flutter/pub-resolved.txt",
    "deps/flutter/pub-sources.txt",
    "deps/flutter/package-resolve-paths.txt",
    "deps/node/node-resolved.txt",
    "deps/node/node-sources.txt",
    "deps/node/node-resolve-paths.txt",
    "deps/python/python-deps-status.txt",
    # J3
    "security/shadowing-check.txt",
    "security/duplicate-module-names.txt",
    # J4
    "static/ununsed-imports.txt",
    "static/false-integration-check.txt",
    # J5
    "tests/flutter-test-report.txt",
    "tests/nest-test-report.txt",
    "tests/e2e-ws-report.txt",
    # J6
    "observability/trace-export.json",
    "observability/correlation-ids.txt",
    "observability/service-logs.txt",
    "observability/e2e-timeline.txt",
    # J7
    "runbook/repro-steps.md",
    "runbook/versions.txt",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        return
    _ensure_parent(path)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    try:
        ARTIFACTS_ROOT.mkdir(parents=True, exist_ok=True)

        # Minimal placeholder content is intentionally explicit and auditable.
        for rel in REQUIRED_FILES:
            p = ARTIFACTS_ROOT / rel

            if p.suffix.lower() == ".json":
                _write_if_missing(
                    p,
                    json.dumps(
                        {
                            "status": "PLACEHOLDER",
                            "generated_utc": _utc_now(),
                            "note": "This placeholder will be overwritten by CI steps that generate real evidence.",
                            "path": f"artifacts/{rel}",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                )
            else:
                _write_if_missing(
                    p,
                    "\n".join(
                        [
                            f"# PLACEHOLDER ({rel})",
                            "",
                            f"generated_utc: {_utc_now()}",
                            "",
                            "This file is required by PR-2 artifact contract (J1–J7).",
                            "It will be overwritten by real CI evidence in later steps.",
                            "",
                        ]
                    ),
                )

        return 0
    except Exception as e:
        print(f"create_pr_artifacts_skeleton error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

