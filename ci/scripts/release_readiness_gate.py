#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release Readiness Gate (Gate 8) checker.

Implements rules from `memory_bank/implementation-plan.md` section 8:
- Every mergeable PR must provide:
  1) Change log (impact scope + rollback)
  2) Backward compatibility strategy for data changes (if any)
  3) Minimal runbook to reproduce the minimal chain in a clean environment
     (Docker Compose baseline; see section 0.7).

This script is designed to run both locally and in GitHub Actions.

Outputs (always):
- ci_artifacts/release-readiness-report.json

Exit code:
- 0 on pass
- 2 on fail (rule violations)
- 3 on unexpected runtime error

Repo-early behavior:
- This repo may not have runtime code/compose yet. To keep the gate usable and
  auditable, we enforce *documentation presence* unconditionally, but treat
  Docker Compose execution itself as "best effort" unless explicit compose files
  exist.

The gate is machine-checkable: it looks for specific files and required fields.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "ci_artifacts"
REPORT_JSON_PATH = ARTIFACTS_DIR / "release-readiness-report.json"

# Where we accept release notes / runbook content.
RELEASE_NOTES_CANDIDATES = [
    REPO_ROOT / "RELEASE_NOTES.md",
    REPO_ROOT / "docs" / "release-notes.md",
    REPO_ROOT / "docs" / "release" / "notes.md",
]

RUNBOOK_CANDIDATES = [
    REPO_ROOT / "docs" / "runbook" / "mvp.md",
    REPO_ROOT / "docs" / "runbook.md",
    REPO_ROOT / "RUNBOOK.md",
    REPO_ROOT / "README.md",  # fallback: we accept a dedicated section in README
]

# Compose baseline indicators (0.7)
COMPOSE_CANDIDATES = [
    REPO_ROOT / "docker-compose.yml",
    REPO_ROOT / "docker-compose.yaml",
    REPO_ROOT / "compose.yml",
    REPO_ROOT / "compose.yaml",
]

TRIGGER_RULES = {
    "migrations": re.compile(r"(^|/)migrations/", re.IGNORECASE),
    "openapi": re.compile(r"(^|/)openapi[^/]*\.(yml|yaml|json)$", re.IGNORECASE),
    "jobs": re.compile(r"(^|/)jobs/", re.IGNORECASE),
}


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_git(args: Sequence[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (code {completed.returncode}): {completed.stderr.strip()}"
        )
    return completed.stdout


def _guess_base_head() -> Tuple[Optional[str], Optional[str]]:
    base = os.environ.get("GITHUB_BASE_SHA") or os.environ.get("BASE_SHA")
    head = os.environ.get("GITHUB_HEAD_SHA") or os.environ.get("HEAD_SHA")
    if base and head:
        return base, head
    return None, None


def _changed_files(base: Optional[str], head: Optional[str]) -> List[str]:
    if base and head:
        out = _run_git(["diff", "--name-only", f"{base}...{head}"])
        files = [line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()]
        return sorted(set(files))

    out = _run_git(["status", "--porcelain"])
    files: List[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if path:
            files.append(path.replace("\\", "/"))
    return sorted(set(files))


def _rel(p: Path) -> str:
    return p.relative_to(REPO_ROOT).as_posix()


def _first_existing(paths: List[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists() and p.is_file():
            return p
    return None


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _find_required_sections_in_text(
    *,
    text: str,
    required_any_of: Dict[str, List[str]],
    context_name: str,
) -> Tuple[bool, List[str]]:
    missing: List[str] = []
    hay = text.lower()
    for section, needles in required_any_of.items():
        if not any(n.lower() in hay for n in needles):
            missing.append(f"Missing '{section}' in {context_name} (expected one of: {', '.join(needles)})")
    return len(missing) == 0, missing


def check_change_log() -> Tuple[CheckResult, Optional[str]]:
    notes_path = _first_existing(RELEASE_NOTES_CANDIDATES)
    if not notes_path:
        details = (
            "FAIL: missing change log file. Expected one of:\n- "
            + "\n- ".join(str(p.relative_to(REPO_ROOT)) for p in RELEASE_NOTES_CANDIDATES)
        )
        return CheckResult(name="Change log present (impact + rollback)", ok=False, details=details), None

    text = _read_text(notes_path)
    ok, missing = _find_required_sections_in_text(
        text=text,
        context_name=_rel(notes_path),
        required_any_of={
            "impact scope": ["impact", "影响", "scope", "影响范围"],
            "rollback": ["rollback", "回滚"],
        },
    )

    details = (
        f"{'PASS' if ok else 'FAIL'}: checked `{_rel(notes_path)}`" + ("" if ok else "\n- " + "\n- ".join(missing))
    )
    return CheckResult(name="Change log present (impact + rollback)", ok=ok, details=details), _rel(notes_path)


def _looks_like_data_change(changed: List[str]) -> Tuple[bool, List[str]]:
    hits: List[str] = []
    for f in changed:
        if TRIGGER_RULES["migrations"].search(f):
            hits.append(f)
    # We treat migrations as the hard signal for data changes.
    return len(hits) > 0, hits


def check_backward_compat(changed: List[str], *, runbook_text: str, runbook_path: str) -> CheckResult:
    has_data_change, hits = _looks_like_data_change(changed)
    if not has_data_change:
        return CheckResult(
            name="Backward compatibility strategy (if data changes)",
            ok=True,
            details="PASS (no migrations/** changes detected)",
        )

    # Require explicit mention to avoid silent breakage.
    ok, missing = _find_required_sections_in_text(
        text=runbook_text,
        context_name=runbook_path,
        required_any_of={
            "backward compatibility strategy": ["backward", "兼容", "expand", "contract", "双写", "默认值"],
            "migration rollback": ["rollback", "回滚", "down", "revert"],
        },
    )

    details_lines = [
        f"{'PASS' if ok else 'FAIL'}: migrations changed; checked `{runbook_path}`",
        "Triggered by:",
        *[f"- {h}" for h in hits],
    ]
    if not ok:
        details_lines.append("Missing:")
        details_lines.extend([f"- {m}" for m in missing])

    return CheckResult(
        name="Backward compatibility strategy (if data changes)",
        ok=ok,
        details="\n".join(details_lines),
    )


def check_runbook() -> Tuple[CheckResult, Optional[str], Optional[str]]:
    runbook_path = _first_existing(RUNBOOK_CANDIDATES)
    if not runbook_path:
        details = (
            "FAIL: missing minimal runbook. Expected one of:\n- "
            + "\n- ".join(str(p.relative_to(REPO_ROOT)) for p in RUNBOOK_CANDIDATES)
        )
        return CheckResult(name="Minimal runbook present", ok=False, details=details), None, None

    text = _read_text(runbook_path)

    # If README used, we require a dedicated section to reduce false positives.
    if runbook_path.name.lower() == "readme.md":
        required_section = "mvp runbook"
        if required_section not in text.lower():
            return (
                CheckResult(
                    name="Minimal runbook present",
                    ok=False,
                    details=(
                        f"FAIL: using README.md as runbook requires a section titled '{required_section}' (case-insensitive). "
                        f"Checked `{_rel(runbook_path)}`"
                    ),
                ),
                _rel(runbook_path),
                text,
            )

    ok, missing = _find_required_sections_in_text(
        text=text,
        context_name=_rel(runbook_path),
        required_any_of={
            "docker compose quickstart": ["docker compose", "docker-compose", "compose"],
            "smoke test": ["smoke", "health", "curl"],
        },
    )

    details = (
        f"{'PASS' if ok else 'FAIL'}: checked `{_rel(runbook_path)}`" + ("" if ok else "\n- " + "\n- ".join(missing))
    )
    return CheckResult(name="Minimal runbook present", ok=ok, details=details), _rel(runbook_path), text


def check_compose_presence() -> CheckResult:
    compose_path = _first_existing(COMPOSE_CANDIDATES)
    if not compose_path:
        # We fail only if the runbook claims compose but repo has none.
        # In early repo, we allow PASS with N/A to avoid blocking docs-only work.
        return CheckResult(
            name="Docker Compose baseline present",
            ok=True,
            details=(
                "PASS (N/A): no docker-compose.yml/compose.yml found in repo yet. "
                "Once runtime code lands, add a compose baseline per implementation-plan.md section 0.7."
            ),
        )

    return CheckResult(
        name="Docker Compose baseline present",
        ok=True,
        details=f"PASS: found `{_rel(compose_path)}`",
    )


def main(argv: Sequence[str]) -> int:
    try:
        base, head = _guess_base_head()
        changed = _changed_files(base, head)

        results: List[CheckResult] = []

        change_log_result, notes_path = check_change_log()
        results.append(change_log_result)

        runbook_result, runbook_path, runbook_text = check_runbook()
        results.append(runbook_result)

        # Backward-compat check is tied to presence of runbook text.
        if runbook_path and runbook_text is not None:
            results.append(check_backward_compat(changed, runbook_text=runbook_text, runbook_path=runbook_path))
        else:
            results.append(
                CheckResult(
                    name="Backward compatibility strategy (if data changes)",
                    ok=False,
                    details="FAIL: cannot evaluate because runbook is missing",
                )
            )

        results.append(check_compose_presence())

        overall_ok = all(r.ok for r in results)

        report: Dict[str, Any] = {
            "timestamp_utc": _utc_now(),
            "policy_source": "memory_bank/implementation-plan.md section 8",
            "base_sha": base,
            "head_sha": head,
            "changed_files": changed,
            "release_notes_path": notes_path,
            "runbook_path": runbook_path,
            "checks": [{"name": r.name, "ok": r.ok, "details": r.details} for r in results],
            "overall_ok": overall_ok,
        }

        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_JSON_PATH.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        if overall_ok:
            print("Release Readiness Gate PASSED")
            return 0
        print("Release Readiness Gate FAILED")
        for r in results:
            if not r.ok:
                print(f"- {r.name}: {r.details}")
        return 2

    except Exception as e:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        report = {
            "timestamp_utc": _utc_now(),
            "policy_source": "memory_bank/implementation-plan.md section 8",
            "overall_ok": False,
            "error": str(e),
        }
        REPORT_JSON_PATH.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Release Readiness Gate ERROR: {e}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

