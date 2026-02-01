#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create PR evidence artifacts skeleton.

Creates the fixed `artifacts/` directory structure and required placeholder files
(per PR-2 J list). This is used in CI so that later gates can populate real

Notes:
- Contents are placeholders; the existence is what's enforced in PR-1.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES_WITH_CONTENT = {
    "artifacts/runbook/repro-steps.md": "# PR Repro Steps\n\nplaceholder (early-repo)\n",
    "artifacts/runbook/versions.txt": "placeholder (early-repo)\n",
    "artifacts/audit/dependency-integrity-report.md": "# Dependency Integrity Report\n\nplaceholder (early-repo)\n",
}

REQUIRED_EMPTY_FILES = [
    # J1
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
]


def _ensure_file(path: Path, content: str | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if content is None:
        if not path.exists():
            path.write_text("", encoding="utf-8")
    else:
        # Always ensure file exists with baseline content; don't overwrite if already present.
        if not path.exists():
            path.write_text(content, encoding="utf-8")


def main() -> int:
    for rel, content in REQUIRED_FILES_WITH_CONTENT.items():
        _ensure_file(REPO_ROOT / rel, content)

    for rel in REQUIRED_EMPTY_FILES:
        _ensure_file(REPO_ROOT / rel, None)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

