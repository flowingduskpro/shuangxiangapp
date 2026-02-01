#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MVP Scope Gate (Gate 7) checker.

Implements rules from `memory_bank/implementation-plan.md` section 7.

Goal (MVP): prevent non-MVP capabilities from entering main by enforcing a
repo-auditable hard-fail keyword blacklist across the PR change set.

Contract:
- Always produce: `ci_artifacts/mvp-scope-report.json`
- Exit code:
  - 0 on pass (including N/A)
  - 2 on fail (rule violations)
  - 3 on unexpected runtime error

Machine-checkable rules (current):
- Read policy from `ci/mvp-scope-rules.yml`.
- Determine the change set (best effort):
  - If BASE_SHA/HEAD_SHA (or GitHub equivalents) exist, use `git diff --name-only base...head`.
  - Else, fall back to `git status --porcelain` (staged + unstaged) vs HEAD.
- Scan each changed file:
  - Always scan the normalized path string (POSIX style).
  - Optionally scan file content as text when:
    - file exists in workspace, and
    - size <= max_file_bytes (default 300KB), and
    - extension is in an allowlist OR file is detected as text (best-effort).
- A match occurs when any `hard_fail_keywords` occurs as a substring in either
  the path or content (case-insensitive when configured).

Docs-only / early-repo behavior:
- If the change set is empty OR only includes docs/config files (no *.dart/*.ts/*.py changes),
  conclusion is N/A and the gate passes.
  Rationale: section 7 is about preventing non-MVP features in code; docs-only PRs should
  not be blocked (while still producing an auditable report).

Notes:
- This gate intentionally does not depend on network access.
- This gate is conservative: it may produce false positives for generic keywords like
  "monitor" in non-feature contexts. If that becomes an issue, tighten the keyword list
  or introduce explicit allowlist exceptions with evidence.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "ci_artifacts"
REPORT_JSON_PATH = ARTIFACTS_DIR / "mvp-scope-report.json"
RULES_PATH = REPO_ROOT / "ci" / "mvp-scope-rules.yml"

DEFAULT_MAX_FILE_BYTES = 300_000
CODE_EXTS = {".dart", ".ts", ".py"}

# Exclude gate/tooling/docs areas from *content* scanning to avoid self-trigger.
CONTENT_EXCLUDE_PREFIXES = (
    "ci/",
    "memory_bank/",
    "ci_artifacts/",
)


@dataclass
class MatchEvidence:
    keyword: str
    target: str  # path/content
    file: str
    sample: str


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


def _is_probably_text(data: bytes) -> bool:
    # Best-effort heuristic: reject NUL bytes.
    return b"\x00" not in data


def _load_rules() -> Dict[str, Any]:
    if not RULES_PATH.exists():
        raise RuntimeError(f"Missing rules file: {RULES_PATH}")

    # Minimal YAML reader (no external deps).
    # Supports:
    # - top-level scalars (e.g., version: 1)
    # - one-level nested mapping for `match` (case_insensitive, targets)
    # - top-level lists for `hard_fail_keywords` and `notes`
    rules: Dict[str, Any] = {}
    current_top_list: Optional[str] = None
    current_map_key: Optional[str] = None

    def _as_scalar(v: str) -> Any:
        if v.isdigit():
            return int(v)
        if v.lower() in ("true", "false"):
            return v.lower() == "true"
        return v.strip('"')

    for raw in RULES_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue

        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()

        # Nested map entry (only support under a current map key like `match:`)
        if indent >= 2 and current_map_key and ":" in line and not line.startswith("-"):
            k, rest = line.split(":", 1)
            k = k.strip()
            rest = rest.strip()
            if isinstance(rules.get(current_map_key), dict):
                rules[current_map_key][k] = _as_scalar(rest)
            continue

        # List item
        if line.startswith("-"):
            item = line[1:].strip().strip('"')
            if current_top_list and isinstance(rules.get(current_top_list), list):
                rules[current_top_list].append(item)
            continue

        # New mapping key
        if ":" in line:
            k, rest = line.split(":", 1)
            k = k.strip()
            rest = rest.strip()

            current_top_list = None
            current_map_key = None

            if rest == "":
                # container (list or map) - decide later based on following lines; initialize as empty list
                # If key is `match`, treat as dict.
                if k == "match":
                    rules[k] = {}
                    current_map_key = k
                else:
                    rules[k] = []
                    current_top_list = k
            else:
                rules[k] = _as_scalar(rest)

    return rules


def _write_report(report: Dict[str, Any]) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _scan_file_content(
    *,
    abs_path: Path,
    keyword: str,
    case_insensitive: bool,
    max_bytes: int,
) -> Optional[str]:
    if not abs_path.exists() or not abs_path.is_file():
        return None
    try:
        size = abs_path.stat().st_size
        if size > max_bytes:
            return None
        data = abs_path.read_bytes()
        if not _is_probably_text(data):
            return None
        text = data.decode("utf-8", errors="replace")
    except Exception:
        return None

    haystack = text.lower() if case_insensitive else text
    needle = keyword.lower() if case_insensitive else keyword

    idx = haystack.find(needle)
    if idx < 0:
        return None

    start = max(0, idx - 80)
    end = min(len(text), idx + len(keyword) + 80)
    snippet = text[start:end].replace("\n", "\\n")
    return snippet


def main(argv: Sequence[str]) -> int:
    try:
        rules = _load_rules()
        match_cfg = rules.get("match") if isinstance(rules.get("match"), dict) else {}
        case_insensitive = bool(match_cfg.get("case_insensitive", True))
        targets = (
            match_cfg.get("targets")
            if isinstance(match_cfg.get("targets"), list)
            else ["path", "content"]
        )
        hard_fail_keywords = (
            rules.get("hard_fail_keywords")
            if isinstance(rules.get("hard_fail_keywords"), list)
            else []
        )
        max_file_bytes = int(rules.get("max_file_bytes", DEFAULT_MAX_FILE_BYTES))

        base, head = _guess_base_head()
        changed = _changed_files(base, head)

        changed_code_files = [f for f in changed if Path(f).suffix.lower() in CODE_EXTS]
        docs_only = len(changed_code_files) == 0

        evidences: List[MatchEvidence] = []

        if hard_fail_keywords and changed:
            for f in changed:
                posix_path = f.replace("\\", "/")
                abs_path = REPO_ROOT / Path(posix_path)
                is_code_file = Path(posix_path).suffix.lower() in CODE_EXTS
                excluded_from_content = posix_path.lower().startswith(
                    tuple(p.lower() for p in CONTENT_EXCLUDE_PREFIXES)
                )

                for kw in hard_fail_keywords:
                    if not isinstance(kw, str) or not kw.strip():
                        continue
                    keyword = kw.strip()

                    # Path scan (always)
                    if "path" in targets:
                        hay = posix_path.lower() if case_insensitive else posix_path
                        needle = keyword.lower() if case_insensitive else keyword
                        if needle in hay:
                            evidences.append(
                                MatchEvidence(
                                    keyword=keyword,
                                    target="path",
                                    file=posix_path,
                                    sample=posix_path,
                                )
                            )
                            continue

                    # Content scan (only for business code files to reduce false positives on docs/tooling)
                    if "content" in targets and is_code_file and not excluded_from_content:
                        snippet = _scan_file_content(
                            abs_path=abs_path,
                            keyword=keyword,
                            case_insensitive=case_insensitive,
                            max_bytes=max_file_bytes,
                        )
                        if snippet is not None:
                            evidences.append(
                                MatchEvidence(
                                    keyword=keyword,
                                    target="content",
                                    file=posix_path,
                                    sample=snippet,
                                )
                            )

        if not changed:
            conclusion = "N/A"
            overall_ok = True
            summary = "No changed files detected"
        elif docs_only:
            conclusion = "N/A"
            overall_ok = True
            summary = "Docs-only/config-only change set (no *.dart/*.ts/*.py changes)"
        elif evidences:
            conclusion = "FAIL"
            overall_ok = False
            summary = f"Matched hard-fail keywords: {len(evidences)} occurrence(s)"
        else:
            conclusion = "PASS"
            overall_ok = True
            summary = "No hard-fail keywords matched"

        report: Dict[str, Any] = {
            "timestamp_utc": _utc_now(),
            "policy_source": "memory_bank/implementation-plan.md section 7",
            "rules_path": _rel(RULES_PATH),
            "base_sha": base,
            "head_sha": head,
            "changed_files": changed,
            "changed_code_files": changed_code_files,
            "conclusion": conclusion,
            "overall_ok": overall_ok,
            "summary": summary,
            "matches": [
                {
                    "keyword": e.keyword,
                    "target": e.target,
                    "file": e.file,
                    "sample": e.sample,
                }
                for e in evidences
            ],
        }

        _write_report(report)

        if overall_ok:
            print("MVP Scope Gate PASSED")
            print(f"Report written: {REPORT_JSON_PATH}")
            return 0

        print("MVP Scope Gate FAILED:", file=sys.stderr)
        for e in evidences[:20]:
            print(
                f"- matched `{e.keyword}` in {e.target} of `{e.file}` (sample: {e.sample[:160]})",
                file=sys.stderr,
            )
        if len(evidences) > 20:
            print(f"- ... and {len(evidences) - 20} more", file=sys.stderr)
        print(f"\nSee report: {REPORT_JSON_PATH}", file=sys.stderr)
        return 2

    except Exception as e:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        _write_report(
            {
                "timestamp_utc": _utc_now(),
                "conclusion": "FAIL",
                "overall_ok": False,
                "summary": f"runtime error: {e}",
            }
        )
        print(f"MVP Scope Gate runtime error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
