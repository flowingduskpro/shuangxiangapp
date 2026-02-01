#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate PR-2 evidence artifacts tree.

This script is the single entry point to produce artifacts/* required by:
- memory_bank/implementation-plan.md (J1–J7)
- PR-2 acceptance criteria (K1–K3)

Contract:
- Must write all required files under artifacts/ (see create_pr_artifacts_skeleton.py).
- Must not fake integrations: if a stack isn't implemented yet, clearly mark N/A.

Current stage:
- Produces dependency and env evidence.
- Delegates to `dependency_integrity_report.py` so the 1–40 list is always generated.
- Leaves runtime evidence to dedicated runners (e2e + observability export).
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ART = REPO_ROOT / "artifacts"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    p = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr


def main() -> int:
    # Ensure skeleton exists
    rc, _out, err = _run([
        "python",
        str(REPO_ROOT / "ci" / "scripts" / "create_pr_artifacts_skeleton.py"),
    ], cwd=REPO_ROOT)
    if rc != 0:
        raise RuntimeError(f"create_pr_artifacts_skeleton.py failed (rc={rc}): {err}")

    # Generate dependency integrity report (1–40 full list)
    rc, out, err = _run([
        "python",
        str(REPO_ROOT / "ci" / "scripts" / "dependency_integrity_report.py"),
    ], cwd=REPO_ROOT)
    if rc != 0:
        raise RuntimeError(f"dependency_integrity_report.py failed (rc={rc}): {err}")

    # versions.txt
    versions = {
        "timestamp_utc": _utc(),
        "os": platform.platform(),
        "python": platform.python_version(),
    }
    _write(ART / "runbook" / "versions.txt", json.dumps(versions, ensure_ascii=False, indent=2) + "\n")

    # Node deps evidence (best-effort, no network)
    repo_pkg_lock = REPO_ROOT / "package-lock.json"
    if repo_pkg_lock.exists():
        _write(ART / "deps" / "node" / "node-sources.txt", "source: npm registry (lockfile present)\n")
        _write(ART / "deps" / "node" / "node-resolved.txt", repo_pkg_lock.read_text(encoding="utf-8", errors="replace")[:200000])
        # resolve paths proof
        rc, out, err = _run([
            "node",
            "-p",
            "JSON.stringify({nestjs:require.resolve('@nestjs/core'), prisma:require.resolve('@prisma/client'), ioredis:require.resolve('ioredis')}, null, 2)",
        ], cwd=REPO_ROOT)
        if rc == 0:
            _write(ART / "deps" / "node" / "node-resolve-paths.txt", out + "\n")
        else:
            _write(ART / "deps" / "node" / "node-resolve-paths.txt", f"N/A (resolve failed)\nrc={rc}\n{err}\n")
    else:
        _write(ART / "deps" / "node" / "node-sources.txt", "N/A\n")
        _write(ART / "deps" / "node" / "node-resolved.txt", "N/A\n")
        _write(ART / "deps" / "node" / "node-resolve-paths.txt", "N/A\n")

    # Flutter/Python deps placeholders (until stacks land)
    for rel in [
        ART / "deps" / "flutter" / "pub-resolved.txt",
        ART / "deps" / "flutter" / "pub-sources.txt",
        ART / "deps" / "flutter" / "package-resolve-paths.txt",
        ART / "deps" / "python" / "python-deps-status.txt",
    ]:
        if not rel.exists():
            _write(rel, "N/A\n")

    # Security/static placeholders will be overwritten by real scanners later
    for rel in [
        ART / "security" / "shadowing-check.txt",
        ART / "security" / "duplicate-module-names.txt",
        ART / "static" / "ununsed-imports.txt",
        ART / "static" / "false-integration-check.txt",
    ]:
        if not rel.exists():
            _write(rel, "N/A\n")

    # Tests placeholders (will be replaced by real runs)
    for rel in [
        ART / "tests" / "flutter-test-report.txt",
        ART / "tests" / "nest-test-report.txt",
        ART / "tests" / "e2e-ws-report.txt",
    ]:
        if not rel.exists():
            _write(rel, "PENDING\n")

    # Observability placeholders: only write if files do not exist yet.
    obs_placeholders = {
        "trace-export.json": "{\n  \"status\": \"PENDING\",\n  \"note\": \"Will be overwritten by real OTel export\"\n}\n",
        "correlation-ids.txt": "placeholder-correlation_id\n",
        "service-logs.txt": "x-correlation-id placeholder-x-correlation-id\ncorrelation_id placeholder-correlation_id\nclass_session_id placeholder-class_session_id\n",
        "e2e-timeline.txt": "PENDING\n",
    }

    for name, content in obs_placeholders.items():
        p = ART / "observability" / name
        if not p.exists():
            _write(p, content)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
