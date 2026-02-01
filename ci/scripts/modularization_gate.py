#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Modularization Gate (Step 9) checker.

Purpose
-------
Turn `memory_bank/implementation-plan.md` section 9 ("模块化" & "依赖黑箱") into a
machine-checkable, auditable gate.

Early-repo strategy
-------------------
If the repo has no manifest files AND there is no business source code under the
configured roots (default: apps/, services/), the gate returns PASS (N/A) but
still produces an artifact.

Outputs (always)
----------------
- ci_artifacts/modularization-report.json

Exit code
---------
- 0 on pass
- 2 on fail (rule violations)
- 3 on unexpected runtime error

Notes
-----
This gate is intentionally conservative and explainable:
- It focuses on directory/path policies first (fast, stable, low false positives).
- As real code lands, it can be upgraded to dependency graphs/import rules.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "ci_artifacts"
REPORT_JSON_PATH = ARTIFACTS_DIR / "modularization-report.json"

DEFAULT_SCAN_ROOTS = ["apps", "services"]
BUSINESS_EXTS = {".dart", ".ts", ".py"}

MANIFEST_RELS = [
    "pubspec.yaml",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
]

# Exclusions aligned with implementation-plan.md 0.4 and Gate 3.
EXCLUDE_DIR_PATTERNS = [
    re.compile(r"(^|/)generated(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)build(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)dist(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)node_modules(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)\.dart_tool(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)\.venv(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)__pycache__(/|$)", re.IGNORECASE),
]

EXCLUDE_FILE_PATTERNS = [
    re.compile(r"\.g\.dart$", re.IGNORECASE),
    re.compile(r"\.d\.ts$", re.IGNORECASE),
    re.compile(r"\.pb\.[^/]+$", re.IGNORECASE),
]

# Conservative "anti-common-layer" signal directories.
# We DO NOT ban all utils/common globally forever; we only flag in business roots.
BANNED_GENERAL_LAYER_DIR_NAMES = {
    "shared",
    "common",
    "utils",
}

# Conservative "vendored dependency source" directories.
BANNED_VENDOR_DIR_NAMES = {
    "vendor",
    "third_party",
    "third-party",
}


@dataclass
class Finding:
    rule: str
    path: str
    message: str


def _is_excluded(rel_posix: str) -> bool:
    return any(rx.search(rel_posix) for rx in EXCLUDE_DIR_PATTERNS) or any(
        rx.search(rel_posix) for rx in EXCLUDE_FILE_PATTERNS
    )


def _parse_roots(argv: Sequence[str]) -> List[str]:
    # CLI: --roots apps,services
    roots: List[str] = []
    if "--roots" in argv:
        idx = argv.index("--roots")
        if idx + 1 < len(argv):
            candidate = argv[idx + 1]
            roots = [x.strip().strip("/") for x in candidate.split(",") if x.strip()]

    # Env override takes precedence
    env = os.environ.get("MODULARIZATION_GATE_ROOTS")
    if env:
        roots = [x.strip().strip("/") for x in env.split(",") if x.strip()]

    return roots if roots else list(DEFAULT_SCAN_ROOTS)


def _iter_business_files(scan_roots: List[str]) -> Iterable[Path]:
    for root in scan_roots:
        root_path = REPO_ROOT / root
        if not root_path.exists() or not root_path.is_dir():
            continue
        for p in root_path.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(REPO_ROOT).as_posix()
            if _is_excluded(rel):
                continue
            if p.suffix.lower() not in BUSINESS_EXTS:
                continue
            yield p


def _manifest_presence() -> Dict[str, bool]:
    return {m: (REPO_ROOT / m).exists() for m in MANIFEST_RELS}


def _has_any_manifest(presence: Dict[str, bool]) -> bool:
    return any(presence.values())


def _has_any_business_code(scan_roots: List[str]) -> bool:
    return any(True for _ in _iter_business_files(scan_roots))


def _scan_banned_directories(scan_roots: List[str]) -> List[Finding]:
    findings: List[Finding] = []

    # We walk directories under scan roots and flag on directory-name matches.
    for root in scan_roots:
        root_path = REPO_ROOT / root
        if not root_path.exists() or not root_path.is_dir():
            continue

        for p in root_path.rglob("*"):
            if not p.is_dir():
                continue
            rel = p.relative_to(REPO_ROOT).as_posix()
            if _is_excluded(rel):
                continue

            name = p.name.lower()
            if name in BANNED_GENERAL_LAYER_DIR_NAMES:
                findings.append(
                    Finding(
                        rule="no_general_shared_layer",
                        path=rel,
                        message=(
                            "Found a generic shared layer directory. "
                            "Step 9 forbids building a self-made general layer; prefer mature deps "
                            "or keep code within a bounded module."
                        ),
                    )
                )

            if name in BANNED_VENDOR_DIR_NAMES:
                findings.append(
                    Finding(
                        rule="no_vendored_dependency_source",
                        path=rel,
                        message=(
                            "Found a vendored/third-party source directory. "
                            "This is a common sign of copying dependency code into the repo, "
                            "which violates dependency integrity/blackbox principles unless explicitly audited."
                        ),
                    )
                )

    return findings


def _write_report(*, report: Dict[str, Any]) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: List[str]) -> int:
    scan_roots = _parse_roots(argv)
    manifest_presence = _manifest_presence()
    any_manifest = _has_any_manifest(manifest_presence)
    any_business = _has_any_business_code(scan_roots)

    utc_now = datetime.now(timezone.utc).isoformat()

    # Early repo: no manifest and no business code under roots => N/A pass.
    is_na = (not any_manifest) and (not any_business)

    findings: List[Finding] = []
    if not is_na:
        findings = _scan_banned_directories(scan_roots)

    overall_ok = len(findings) == 0

    report: Dict[str, Any] = {
        "timestamp_utc": utc_now,
        "gate": "modularization_gate",
        "scan_roots": scan_roots,
        "manifest_presence": manifest_presence,
        "has_any_manifest": any_manifest,
        "has_any_business_code": any_business,
        "is_na": is_na,
        "why_na": (
            "No manifest files and no business source code detected under scan roots. "
            "This gate will become strict once a manifest or business code appears."
            if is_na
            else ""
        ),
        "findings": [
            {"rule": f.rule, "path": f.path, "message": f.message} for f in findings
        ],
        "overall_ok": overall_ok,
        "artifacts": {
            "report_json": str(REPORT_JSON_PATH.relative_to(REPO_ROOT).as_posix())
        },
        "next_tighten_conditions": {
            "become_strict_when_any_manifest_exists": True,
            "become_strict_when_business_code_exists_under_scan_roots": True,
        },
    }

    _write_report(report=report)

    if overall_ok:
        if is_na:
            print("Modularization Gate PASSED (N/A)")
        else:
            print("Modularization Gate PASSED")
        return 0

    print("Modularization Gate FAILED")
    for f in findings:
        print(f"- [{f.rule}] {f.path}: {f.message}")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as e:
        # Still try to write an error report.
        try:
            utc_now = datetime.now(timezone.utc).isoformat()
            _write_report(
                report={
                    "timestamp_utc": utc_now,
                    "gate": "modularization_gate",
                    "overall_ok": False,
                    "is_na": False,
                    "error": str(e),
                }
            )
        except Exception:
            pass
        print(f"Modularization Gate ERROR: {e}", file=sys.stderr)
        raise SystemExit(3)

