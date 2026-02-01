#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests Gate (Gate 5) checker.

Implements `memory_bank/implementation-plan.md` section 5 (minimal, repo-aware).

Goal (MVP): enforce that each stack has *some* test capability wired up.
Because this repo may be in a docs-only phase, the gate supports N/A and PASS
when no code roots exist yet.

Contract:
- Always produce: `ci_artifacts/tests-report.json`
- Exit code:
  - 0 on pass (including N/A)
  - 2 on fail (rule violations)
  - 3 on unexpected runtime error

Current minimal machine-checkable rules:
- If a Flutter app exists (pubspec.yaml present): require `integration_test/` OR `test/`.
- If a Node service exists (package.json present): require a recognizable test setup:
  - `test/` or `__tests__/` directory, OR
  - `jest` in devDependencies, OR
  - `test` script present in package.json.
- If a Python service exists (requirements/pyproject present): require `tests/` directory.

Notes:
- This gate does not execute tests yet. It verifies *presence and wiring* only,
  keeping it deterministic and toolchain-independent.
- When the repo has runnable code, we can tighten this to actually run unit/integration
  tests in CI.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "ci_artifacts"
REPORT_JSON_PATH = ARTIFACTS_DIR / "tests-report.json"


@dataclass
class CheckResult:
    name: str
    ok: bool
    conclusion: str  # PASS/FAIL/N/A
    evidence: str
    risk: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_report(report: Dict[str, Any]) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


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


def _rel(p: Path) -> str:
    return p.relative_to(REPO_ROOT).as_posix()


def _flutter_check() -> CheckResult:
    pubspecs = _iter_files_by_name("pubspec.yaml")
    if not pubspecs:
        return CheckResult(
            name="Flutter test capability",
            ok=True,
            conclusion="N/A",
            evidence="repo scan found 0 pubspec.yaml",
            risk="N/A",
        )

    # If any flutter project exists, require at least one has integration_test or test.
    missing: List[str] = []
    for pubspec in pubspecs:
        root = pubspec.parent
        has = (root / "integration_test").exists() or (root / "test").exists()
        if not has:
            missing.append(_rel(root))

    if len(missing) == 0:
        return CheckResult(
            name="Flutter test capability",
            ok=True,
            conclusion="PASS",
            evidence="All detected Flutter roots contain integration_test/ or test/",
            risk="N/A",
        )

    return CheckResult(
        name="Flutter test capability",
        ok=False,
        conclusion="FAIL",
        evidence="Missing integration_test/ or test/ in:\n- " + "\n- ".join(missing),
        risk="Without Flutter tests, app regressions (navigation/session state/perf) won't be caught",
    )


def _read_package_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _node_check() -> CheckResult:
    pkgs = _iter_files_by_name("package.json")
    if not pkgs:
        return CheckResult(
            name="Node (NestJS) test capability",
            ok=True,
            conclusion="N/A",
            evidence="repo scan found 0 package.json",
            risk="N/A",
        )

    failures: List[str] = []
    for pkg_path in pkgs:
        root = pkg_path.parent
        try:
            data = _read_package_json(pkg_path)
        except Exception as e:
            failures.append(f"{_rel(pkg_path)} (invalid JSON: {e})")
            continue

        has_test_dir = (root / "test").exists() or (root / "__tests__").exists()
        scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
        has_test_script = isinstance(scripts, dict) and "test" in scripts
        dev_deps = data.get("devDependencies") if isinstance(data.get("devDependencies"), dict) else {}
        has_jest = isinstance(dev_deps, dict) and ("jest" in dev_deps or "@jest" in " ".join(dev_deps.keys()))

        if not (has_test_dir or has_test_script or has_jest):
            failures.append(_rel(root))

    if not failures:
        return CheckResult(
            name="Node (NestJS) test capability",
            ok=True,
            conclusion="PASS",
            evidence="All detected Node roots have test directory and/or test script/jest wiring",
            risk="N/A",
        )

    return CheckResult(
        name="Node (NestJS) test capability",
        ok=False,
        conclusion="FAIL",
        evidence="Missing test setup (test/__tests__ OR scripts.test OR jest devDependency) in:\n- "
        + "\n- ".join(failures),
        risk="Without server tests, contract/auth/validation regressions may slip into main",
    )


def _python_check() -> CheckResult:
    # treat any Python manifest as "python project exists"
    reqs = _iter_files_by_name("requirements.txt")
    pyprojects = _iter_files_by_name("pyproject.toml")

    if not reqs and not pyprojects:
        return CheckResult(
            name="Python (FastAPI) test capability",
            ok=True,
            conclusion="N/A",
            evidence="repo scan found no requirements.txt or pyproject.toml",
            risk="N/A",
        )

    # if any manifest exists, require a tests/ folder in that same dir
    manifests = reqs + pyprojects
    missing: List[str] = []
    for m in manifests:
        root = m.parent
        if not (root / "tests").exists():
            missing.append(_rel(root))

    if not missing:
        return CheckResult(
            name="Python (FastAPI) test capability",
            ok=True,
            conclusion="PASS",
            evidence="All detected Python roots contain tests/ directory",
            risk="N/A",
        )

    return CheckResult(
        name="Python (FastAPI) test capability",
        ok=False,
        conclusion="FAIL",
        evidence="Missing tests/ directory in:\n- " + "\n- ".join(missing),
        risk="Without pytest/golden tests, OCR/extraction/recommendation regressions won't be caught",
    )


def main(argv: Sequence[str]) -> int:
    try:
        checks = [_flutter_check(), _node_check(), _python_check()]
        overall_ok = all(c.ok for c in checks)

        report: Dict[str, Any] = {
            "timestamp_utc": _utc_now(),
            "policy_source": "memory_bank/implementation-plan.md section 5",
            "checks": [
                {
                    "name": c.name,
                    "ok": c.ok,
                    "conclusion": c.conclusion,
                    "evidence": c.evidence,
                    "risk": c.risk,
                }
                for c in checks
            ],
            "overall_ok": overall_ok,
        }
        _write_report(report)

        if overall_ok:
            print("Tests Gate PASSED")
            print(f"Report written: {REPORT_JSON_PATH}")
            return 0

        print("Tests Gate FAILED:", file=sys.stderr)
        for c in checks:
            if not c.ok:
                print(f"- {c.name}: {c.evidence}", file=sys.stderr)
        print(f"\nSee report: {REPORT_JSON_PATH}", file=sys.stderr)
        return 2

    except Exception as e:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        _write_report(
            {
                "timestamp_utc": _utc_now(),
                "overall_ok": False,
                "runtime_error": str(e),
            }
        )
        print(f"Tests Gate runtime error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

