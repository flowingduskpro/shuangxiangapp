#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structure Gate (Gate 3) checker.

Implements rules from `memory_bank/implementation-plan.md` section 3:
- 3.1 Business source file line limit (>250) with whitelist exceptions
- 3.2 Domain directory same-level file count limits
- 3.3 Boundary import checks (best-effort; currently informational unless rules are configured)

This script is designed to run both locally and in GitHub Actions.

Outputs (always):
- ci_artifacts/structure-report.json

Exit code:
- 0 on pass
- 2 on fail (rule violations)
- 3 on unexpected runtime error

Notes:
- Gate 3 applies to "business source". By default, we only scan under repo roots:
  - apps/
  - services/
  Override with env `STRUCTURE_GATE_ROOTS` (comma-separated) or CLI `--roots`.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "ci_artifacts"
REPORT_JSON_PATH = ARTIFACTS_DIR / "structure-report.json"

LINE_LIMIT = 250

# Only count business source files.
BUSINESS_EXTS = {".dart", ".ts", ".py"}

# Exclusions per implementation plan 0.4
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

WHITELIST_PATH = REPO_ROOT / "ci" / "line-limit-whitelist.json"

# Directory file count limits
FLUTTER_NEST_SAME_LEVEL_LIMIT = 25
FASTAPI_SAME_LEVEL_LIMIT = 20

DEFAULT_SCAN_ROOTS = ["apps", "services"]


@dataclass
class Violation:
    kind: str
    path: str
    details: str


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

    # Env override (takes precedence if set)
    env: str | None
    try:
        import os

        env = os.environ.get("STRUCTURE_GATE_ROOTS")
    except Exception:
        env = None

    if env:
        roots = [x.strip().strip("/") for x in env.split(",") if x.strip()]

    return roots if roots else list(DEFAULT_SCAN_ROOTS)


def _iter_business_files(scan_roots: List[str]) -> Iterable[Path]:
    # If the repo doesn't have these directories yet, treat as empty (pass).
    for root in scan_roots:
        root_path = (REPO_ROOT / root)
        if not root_path.exists() or not root_path.is_dir():
            continue
        for p in root_path.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(REPO_ROOT).as_posix()
            if _is_excluded(rel):
                continue
            yield p


def _read_whitelist() -> Dict[str, Dict[str, Any]]:
    if not WHITELIST_PATH.exists():
        return {}
    try:
        data = json.loads(WHITELIST_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Invalid whitelist JSON at {WHITELIST_PATH}: {e}")

    # Accept either list of entries or a dict with 'items'.
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise RuntimeError(
            "Whitelist must be a JSON array or an object containing an 'items' array"
        )

    by_path: Dict[str, Dict[str, Any]] = {}
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip().replace("\\", "/")
        if not path:
            continue
        # Minimal required fields for auditability
        if not item.get("reason") or not item.get("expires_at"):
            raise RuntimeError(
                f"Whitelist entry #{idx} for path '{path}' must include reason and expires_at"
            )
        by_path[path] = item
    return by_path


def _count_lines(path: Path) -> int:
    # Count physical lines to keep it simple and reproducible.
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def _classify_stack(path: Path) -> str:
    # Heuristic: classify by extension.
    ext = path.suffix.lower()
    if ext == ".py":
        return "fastapi"
    if ext == ".dart":
        return "flutter"
    if ext == ".ts":
        return "nestjs"
    return "unknown"


def check_single_file_line_limits(scan_roots: List[str]) -> Tuple[List[Dict[str, Any]], List[Violation]]:
    whitelist = _read_whitelist()
    overs: List[Dict[str, Any]] = []
    violations: List[Violation] = []

    for p in _iter_business_files(scan_roots):
        if p.suffix.lower() not in BUSINESS_EXTS:
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        line_count = _count_lines(p)
        if line_count <= LINE_LIMIT:
            continue

        entry = {
            "path": rel,
            "lines": line_count,
            "stack": _classify_stack(p),
            "whitelisted": rel in whitelist,
        }
        if rel in whitelist:
            entry["whitelist"] = whitelist[rel]
        overs.append(entry)

        if rel not in whitelist:
            violations.append(
                Violation(
                    kind="file_line_limit",
                    path=rel,
                    details=f"{line_count} lines > {LINE_LIMIT} (not whitelisted)",
                )
            )

    overs.sort(key=lambda x: (-(x["lines"]), x["path"]))
    return overs, violations


def _same_level_file_count(dir_path: Path) -> int:
    count = 0
    for child in dir_path.iterdir():
        if not child.is_file():
            continue
        rel = child.relative_to(REPO_ROOT).as_posix()
        if _is_excluded(rel):
            continue
        # Only business source files participate.
        if child.suffix.lower() not in BUSINESS_EXTS:
            continue
        count += 1
    return count


def check_directory_file_counts(scan_roots: List[str]) -> Tuple[List[Dict[str, Any]], List[Violation]]:
    # "Single business domain directory" isn't yet codified in repo structure.
    # We apply the same-level rule to any directory that contains business files.
    records: List[Dict[str, Any]] = []
    violations: List[Violation] = []

    visited: set[str] = set()
    for p in _iter_business_files(scan_roots):
        if p.suffix.lower() not in BUSINESS_EXTS:
            continue
        d = p.parent
        rel_dir = d.relative_to(REPO_ROOT).as_posix()
        if rel_dir in visited:
            continue
        visited.add(rel_dir)

        count = _same_level_file_count(d)
        # determine limit based on dominant stack in dir (python => fastapi limit)
        stack = "fastapi" if any(x.suffix.lower() == ".py" for x in d.glob("*.py")) else "flutter_or_nest"
        limit = FASTAPI_SAME_LEVEL_LIMIT if stack == "fastapi" else FLUTTER_NEST_SAME_LEVEL_LIMIT

        record = {
            "path": rel_dir,
            "same_level_business_file_count": count,
            "limit": limit,
            "stack": stack,
        }
        records.append(record)

        if count > limit:
            violations.append(
                Violation(
                    kind="directory_file_count",
                    path=rel_dir,
                    details=f"{count} files > {limit} (same-level business source files)",
                )
            )

    records.sort(key=lambda x: (-(x["same_level_business_file_count"]), x["path"]))
    return records, violations


def _write_report(
    *,
    scan_roots: List[str],
    file_line_overages: List[Dict[str, Any]],
    directory_counts: List[Dict[str, Any]],
    import_violations: List[Dict[str, Any]],
    violations: List[Violation],
) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    utc_now = datetime.now(timezone.utc).isoformat()

    report: Dict[str, Any] = {
        "timestamp_utc": utc_now,
        "scan_roots": scan_roots,
        "rules": {
            "single_file_line_limit": LINE_LIMIT,
            "dir_same_level_limit": {
                "flutter_or_nest": FLUTTER_NEST_SAME_LEVEL_LIMIT,
                "fastapi": FASTAPI_SAME_LEVEL_LIMIT,
            },
            "counted_exts": sorted(BUSINESS_EXTS),
        },
        "file_line_overages": file_line_overages,
        "directory_same_level_counts": directory_counts,
        "import_boundary_violations": import_violations,
        "violations": [
            {"kind": v.kind, "path": v.path, "details": v.details} for v in violations
        ],
        "overall_ok": len(violations) == 0,
    }

    REPORT_JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: Sequence[str]) -> int:
    try:
        scan_roots = _parse_roots(argv)

        file_line_overages, v1 = check_single_file_line_limits(scan_roots)
        directory_counts, v2 = check_directory_file_counts(scan_roots)

        # Gate 3.3: not enforced yet because repo boundary rules aren't encoded.
        import_violations: List[Dict[str, Any]] = []

        violations = [*v1, *v2]

        _write_report(
            scan_roots=scan_roots,
            file_line_overages=file_line_overages,
            directory_counts=directory_counts,
            import_violations=import_violations,
            violations=violations,
        )

        if violations:
            print("Structure Gate FAILED:", file=sys.stderr)
            for v in violations:
                print(f"- [{v.kind}] {v.path}: {v.details}", file=sys.stderr)
            print(f"\nSee report: {REPORT_JSON_PATH}", file=sys.stderr)
            return 2

        print("Structure Gate PASSED")
        print(f"Report written: {REPORT_JSON_PATH}")
        return 0

    except Exception as e:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            REPORT_JSON_PATH.write_text(
                json.dumps(
                    {
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "overall_ok": False,
                        "runtime_error": str(e),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
