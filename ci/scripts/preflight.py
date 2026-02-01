#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preflight Gate (Gate 2) checker.

Implements rules from `memory_bank/implementation-plan.md`:
- 2.1 Required PR "must-read confirmation" fields
- 2.2 Architecture update coupling when trigger paths were changed

This script is designed to run both locally and in GitHub Actions.

Outputs:
- ci_artifacts/trace-evidence.md (always)
- ci_artifacts/preflight-report.json (always)

Exit code:
- 0 on pass
- 2 on fail (rule violations)
- 3 on unexpected runtime error
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
TRACE_EVIDENCE_PATH = ARTIFACTS_DIR / "trace-evidence.md"
REPORT_JSON_PATH = ARTIFACTS_DIR / "preflight-report.json"

ARCHITECTURE_MD_REL = "memory_bank/architecture.md"
GDD_MD_REL = "memory_bank/双向个性化课堂管理AI App 产品需求与方案生成器 v1.0.0.md"

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
    # Primary: GitHub Actions env
    base = os.environ.get("GITHUB_BASE_SHA") or os.environ.get("BASE_SHA")
    head = os.environ.get("GITHUB_HEAD_SHA") or os.environ.get("HEAD_SHA")
    if base and head:
        return base, head

    # Secondary: derive from current branch vs origin default (best effort)
    # We keep it conservative: if we can't reliably infer, return None.
    return None, None


def changed_files(base: Optional[str], head: Optional[str]) -> List[str]:
    # Use explicit SHAs when available.
    if base and head:
        out = _run_git(["diff", "--name-only", f"{base}...{head}"])
        files = [line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()]
        return sorted(set(files))

    # Local fallback: use staged+unstaged vs HEAD
    out = _run_git(["status", "--porcelain"])
    files: List[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        # format: XY path
        path = line[3:].strip()
        if path:
            files.append(path.replace("\\", "/"))
    return sorted(set(files))


def read_pr_body() -> str:
    # Optional CI override: allow a specific file to supply preflight attestations.
    override_file = os.environ.get("PR_BODY_FILE_OVERRIDE")
    if override_file:
        override_path = Path(override_file)
        if override_path.exists():
            return override_path.read_text(encoding="utf-8")

    # GitHub Actions: parse the event payload
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and Path(event_path).exists():
        try:
            data = json.loads(Path(event_path).read_text(encoding="utf-8"))
            body = (
                data.get("pull_request", {}).get("body")
                or data.get("issue", {}).get("body")
                or ""
            )
            if isinstance(body, str):
                return body
        except Exception:
            # Continue to fallback
            pass

    # Local override: allow providing a text file
    body_file = os.environ.get("PR_BODY_FILE")
    if body_file and Path(body_file).exists():
        return Path(body_file).read_text(encoding="utf-8")

    # Local override: direct string
    return os.environ.get("PR_BODY", "")


def _normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in (text or "").splitlines()).strip()


def check_must_read_confirmation(pr_body: str) -> CheckResult:
    """Gate 2.1

    We don't enforce an exact template, but require these anchors to exist.
    This is strict enough for automation while still being robust.
    """

    body = _normalize(pr_body)
    missing: List[str] = []

    # Must mention both documents explicitly.
    if "memory_bank/architecture.md" not in body and "architecture.md" not in body:
        missing.append("Missing confirmation of reading memory_bank/architecture.md")

    if "方案生成器" not in body and "memory_bank/双向个性化课堂管理AI App 产品需求与方案生成器" not in body:
        missing.append(
            "Missing confirmation of reading GDD doc (memory_bank/双向个性化课堂管理AI App 产品需求与方案生成器 v1.0.0.md)"
        )

    # Business domain: accept any of the domain keywords OR a structured field.
    domain_keywords = ["内容", "课堂", "监控", "反馈", "推荐", "评分", "督导"]
    if not any(k in body for k in domain_keywords) and "业务域" not in body:
        missing.append("Missing business domain declaration (e.g., 内容/课堂/监控/反馈/推荐/评分督导)")

    # Change types: require a line that indicates whether it involves these.
    change_keywords = ["DB", "数据库", "事件", "契约", "权限", "保留", "清理", "合规"]
    if not any(k in body for k in change_keywords) and "是否涉及" not in body:
        missing.append("Missing declaration whether PR impacts DB/events/contracts/auth/retention/compliance")

    ok = len(missing) == 0
    details = "PASS" if ok else "FAIL:\n- " + "\n- ".join(missing)
    return CheckResult(name="Gate 2.1 must-read confirmation", ok=ok, details=details)


def check_architecture_coupling(files: List[str]) -> CheckResult:
    """Gate 2.2

    If changes hit trigger paths, architecture.md must be changed too.
    """

    hits: List[str] = []
    for f in files:
        for label, rx in TRIGGER_RULES.items():
            if rx.search(f):
                hits.append(f"{label}:{f}")

    requires = len(hits) > 0
    has_arch = any(f.lower() == ARCHITECTURE_MD_REL.lower() for f in files)

    if not requires:
        return CheckResult(
            name="Gate 2.2 architecture coupling",
            ok=True,
            details="PASS (no trigger path changes detected)",
        )

    if has_arch:
        return CheckResult(
            name="Gate 2.2 architecture coupling",
            ok=True,
            details="PASS (triggered by changes; architecture.md updated)\nTriggered by:\n- "
            + "\n- ".join(hits),
        )

    return CheckResult(
        name="Gate 2.2 architecture coupling",
        ok=False,
        details=(
            "FAIL: Trigger paths changed but memory_bank/architecture.md was not updated.\n"
            "Triggered by:\n- "
            + "\n- ".join(hits)
            + f"\nRequired file to change: {ARCHITECTURE_MD_REL}"
        ),
    )


def write_artifacts(
    *,
    base: Optional[str],
    head: Optional[str],
    files: List[str],
    pr_body_present: bool,
    results: List[CheckResult],
) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    utc_now = datetime.now(timezone.utc).isoformat()
    overall_ok = all(r.ok for r in results)

    # JSON report
    report: Dict[str, Any] = {
        "timestamp_utc": utc_now,
        "base_sha": base,
        "head_sha": head,
        "changed_files": files,
        "pr_body_present": pr_body_present,
        "checks": [
            {"name": r.name, "ok": r.ok, "details": r.details} for r in results
        ],
        "overall_ok": overall_ok,
    }
    REPORT_JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown evidence
    lines: List[str] = []
    lines.append("# trace-evidence.md")
    lines.append("")
    lines.append("This file is produced by Gate 2 (Preflight) automation.")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- timestamp_utc: `{utc_now}`")
    lines.append(f"- base_sha: `{base or ''}`")
    lines.append(f"- head_sha: `{head or ''}`")
    lines.append(f"- pr_body_present: `{str(pr_body_present).lower()}`")
    lines.append("")
    lines.append("## Changed files")
    if files:
        for f in files:
            lines.append(f"- `{f}`")
    else:
        lines.append("- (none detected)")
    lines.append("")
    lines.append("## Checks")
    for r in results:
        lines.append(f"### {r.name}: {'PASS' if r.ok else 'FAIL'}")
        lines.append("")
        lines.append(r.details)
        lines.append("")

    lines.append("## References")
    lines.append("- memory_bank/implementation-plan.md (Gate 2.1, 2.2, and trigger rules 0.5)")
    lines.append(f"- {ARCHITECTURE_MD_REL}")
    lines.append(f"- {GDD_MD_REL}")

    TRACE_EVIDENCE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    try:
        base, head = _guess_base_head()
        files = changed_files(base, head)
        pr_body = read_pr_body()
        pr_body_present = bool(_normalize(pr_body))

        results: List[CheckResult] = []
        results.append(check_must_read_confirmation(pr_body))
        results.append(check_architecture_coupling(files))

        write_artifacts(
            base=base,
            head=head,
            files=files,
            pr_body_present=pr_body_present,
            results=results,
        )

        if all(r.ok for r in results):
            return 0
        return 2
    except Exception as e:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        TRACE_EVIDENCE_PATH.write_text(
            "# trace-evidence.md\n\nPreflight runtime error:\n\n" + str(e) + "\n",
            encoding="utf-8",
        )
        return 3


if __name__ == "__main__":
    sys.exit(main())
