#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Observability Gate (Gate 6) checker.

Implements rules from `memory_bank/implementation-plan.md` section 6.

Goal (PR-2 MVP): every PR must produce auditable observability evidence for the
end-to-end chain:

WS recv → PG write → Redis update → WS push

Contract:
- Always produce: `ci_artifacts/trace-evidence.md`
- Exit code:
  - 0 on pass
  - 2 on fail (rule violations)
  - 3 on unexpected runtime error

Evidence inputs (PR-2 artifacts tree):
- artifacts/observability/correlation-ids.txt
- artifacts/observability/service-logs.txt
- artifacts/observability/trace-export.json

Pass conditions when code exists:
- Minimal token evidence exists (x-correlation-id / correlation_id / class_session_id)
- trace-export.json is NOT placeholder (must contain `spans` array)
- For at least one correlation_id listed, trace-export.json contains spans with:
  - attributes.correlation_id == that id
  - attributes.class_session_id is present
  - span names cover:
    - ws.message (or ws.event.class_enter)
    - pg.prisma.classEvent.create
    - redis.aggregate.incEnter
    - ws.push.class_session_aggregate

Notes:
- We do not require full parent/child nesting, but require the spans exist in
  the same exported dataset and share correlation_id.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "ci_artifacts"
TRACE_EVIDENCE_PATH = ARTIFACTS_DIR / "trace-evidence.md"

PR2_OBS_DIR = REPO_ROOT / "artifacts" / "observability"
PR2_SERVICE_LOGS = PR2_OBS_DIR / "service-logs.txt"
PR2_CORRELATION_IDS = PR2_OBS_DIR / "correlation-ids.txt"
PR2_TRACE_EXPORT = PR2_OBS_DIR / "trace-export.json"

CORRELATION_HEADER = "x-correlation-id"
CORRELATION_FIELD = "correlation_id"
DEFAULT_BUSINESS_FIELDS = ["class_session_id"]

REQUIRED_SPAN_NAME_SUBSTRINGS = [
    "ws.message",
    "ws.event.class_enter",
    "pg.prisma.classEvent.create",
    "redis.aggregate.incEnter",
    "ws.push.class_session_aggregate",
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    conclusion: str  # PASS/FAIL/N/A
    evidence: str
    risk: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _has_any_manifest() -> bool:
    return any(
        _iter_files_by_name(n)
        for n in ("pubspec.yaml", "package.json", "requirements.txt", "pyproject.toml")
    )


def _write_evidence(*, checks: List[CheckResult], overall_ok: bool) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append("# trace-evidence.md")
    lines.append("")
    lines.append("This file is produced by Gate 6 (Observability Gate) automation.")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- timestamp_utc: `{_utc_now()}`")
    lines.append("")
    lines.append("## Policy")
    lines.append("- Source: `memory_bank/implementation-plan.md` section 6")
    lines.append(f"- Required correlation header: `{CORRELATION_HEADER}`")
    lines.append(f"- Required log field: `{CORRELATION_FIELD}`")
    lines.append(f"- Required business fields (at least one): {', '.join('`'+x+'`' for x in DEFAULT_BUSINESS_FIELDS)}")
    lines.append("- Required spans (as substrings):")
    for s in REQUIRED_SPAN_NAME_SUBSTRINGS:
        lines.append(f"  - `{s}`")
    lines.append("")
    lines.append("## Checks")
    for c in checks:
        lines.append(f"### {c.name}: {c.conclusion}")
        lines.append("")
        lines.append(f"- ok: `{str(c.ok).lower()}`")
        lines.append(f"- evidence: {c.evidence}")
        lines.append(f"- risk: {c.risk}")
        lines.append("")
    lines.append("## Overall")
    lines.append(f"- overall_ok: `{str(overall_ok).lower()}`")
    lines.append("")

    TRACE_EVIDENCE_PATH.write_text("\n".join(lines), encoding="utf-8")


def _check_token_evidence() -> CheckResult:
    if not _has_any_manifest():
        return CheckResult(
            name="Token evidence present",
            ok=True,
            conclusion="N/A",
            evidence="repo scan found no manifests; docs-only phase",
            risk="N/A",
        )

    if not PR2_OBS_DIR.exists():
        return CheckResult(
            name="Token evidence present",
            ok=False,
            conclusion="FAIL",
            evidence=f"Missing required observability dir: `{PR2_OBS_DIR.relative_to(REPO_ROOT).as_posix()}`",
            risk="Without artifacts/observability, MVP trace/log correlation can't be audited",
        )

    if not PR2_SERVICE_LOGS.exists() or not PR2_CORRELATION_IDS.exists():
        missing = []
        if not PR2_SERVICE_LOGS.exists():
            missing.append(PR2_SERVICE_LOGS.relative_to(REPO_ROOT).as_posix())
        if not PR2_CORRELATION_IDS.exists():
            missing.append(PR2_CORRELATION_IDS.relative_to(REPO_ROOT).as_posix())
        return CheckResult(
            name="Token evidence present",
            ok=False,
            conclusion="FAIL",
            evidence="Missing required PR-2 evidence files: " + ", ".join(missing),
            risk="Without these files, correlation ids and service logs for the MVP chain can't be audited",
        )

    text = (
        PR2_SERVICE_LOGS.read_text(encoding="utf-8", errors="replace")
        + "\n"
        + PR2_CORRELATION_IDS.read_text(encoding="utf-8", errors="replace")
    )

    missing: List[str] = []
    if CORRELATION_HEADER not in text:
        missing.append(CORRELATION_HEADER)
    if CORRELATION_FIELD not in text:
        missing.append(CORRELATION_FIELD)
    if not any(bf in text for bf in DEFAULT_BUSINESS_FIELDS):
        missing.append("one of: " + ", ".join(DEFAULT_BUSINESS_FIELDS))

    if not missing:
        return CheckResult(
            name="Token evidence present",
            ok=True,
            conclusion="PASS",
            evidence="artifacts/observability contains required correlation tokens",
            risk="N/A",
        )

    return CheckResult(
        name="Token evidence present",
        ok=False,
        conclusion="FAIL",
        evidence="observability evidence missing tokens: " + ", ".join(missing),
        risk="Without these keys, correlation across logs/traces/DB events won't be verifiable",
    )


def _load_trace_export() -> Dict[str, Any]:
    text = PR2_TRACE_EXPORT.read_text(encoding="utf-8", errors="replace")
    return json.loads(text)


def _check_trace_chain() -> CheckResult:
    if not _has_any_manifest():
        return CheckResult(
            name="Trace chain evidence",
            ok=True,
            conclusion="N/A",
            evidence="repo scan found no manifests; docs-only phase",
            risk="N/A",
        )

    if not PR2_TRACE_EXPORT.exists():
        return CheckResult(
            name="Trace chain evidence",
            ok=False,
            conclusion="FAIL",
            evidence=f"Missing trace export: `{PR2_TRACE_EXPORT.relative_to(REPO_ROOT).as_posix()}`",
            risk="Without trace-export.json, WS→PG→Redis→push chain can't be audited",
        )

    try:
        data = _load_trace_export()
    except Exception as e:
        return CheckResult(
            name="Trace chain evidence",
            ok=False,
            conclusion="FAIL",
            evidence=f"trace-export.json is not valid JSON: {e}",
            risk="Invalid trace export blocks auditing",
        )

    spans = data.get("spans")
    if not isinstance(spans, list) or len(spans) == 0:
        return CheckResult(
            name="Trace chain evidence",
            ok=False,
            conclusion="FAIL",
            evidence="trace-export.json missing non-empty `spans` array (likely placeholder)",
            risk="Placeholder traces are not acceptable for PR-2",
        )

    # Read candidate correlation ids from file.
    ids: List[str] = []
    if PR2_CORRELATION_IDS.exists():
        ids = [x.strip() for x in PR2_CORRELATION_IDS.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]

    if not ids:
        return CheckResult(
            name="Trace chain evidence",
            ok=False,
            conclusion="FAIL",
            evidence="correlation-ids.txt is empty; cannot verify trace linkage",
            risk="Without correlation ids, auditors cannot locate the trace belonging to the E2E run",
        )

    # Normalize spans to (name, attrs)
    def _attrs(s: Any) -> Dict[str, Any]:
        a = s.get("attributes") if isinstance(s, dict) else None
        return a if isinstance(a, dict) else {}

    span_by_corr: Dict[str, List[Dict[str, Any]]] = {}
    for s in spans:
        if not isinstance(s, dict):
            continue
        attrs = _attrs(s)
        corr = attrs.get("correlation_id")
        if isinstance(corr, str) and corr:
            span_by_corr.setdefault(corr, []).append(s)

    # Find an id for which we can assert chain.
    for cid in ids[:10]:
        candidates = span_by_corr.get(cid, [])
        if not candidates:
            continue

        names = [c.get("name") for c in candidates if isinstance(c.get("name"), str)]
        attrs_any = [_attrs(c) for c in candidates]
        has_class_session = any(isinstance(a.get("class_session_id"), str) and a.get("class_session_id") for a in attrs_any)

        # required names: we allow either ws.message or ws.event.class_enter
        has_ws = any(n and ("ws.message" in n or "ws.event.class_enter" in n) for n in names)
        has_pg = any(n and "pg.prisma.classEvent.create" in n for n in names)
        has_redis = any(n and "redis.aggregate.incEnter" in n for n in names)
        has_push = any(n and "ws.push.class_session_aggregate" in n for n in names)

        if has_ws and has_pg and has_redis and has_push and has_class_session:
            return CheckResult(
                name="Trace chain evidence",
                ok=True,
                conclusion="PASS",
                evidence=(
                    f"Found correlated trace spans for correlation_id `{cid}` with required chain spans. "
                    f"trace_file=`{PR2_TRACE_EXPORT.relative_to(REPO_ROOT).as_posix()}`"
                ),
                risk="N/A",
            )

    return CheckResult(
        name="Trace chain evidence",
        ok=False,
        conclusion="FAIL",
        evidence=(
            "No correlation_id in correlation-ids.txt had a complete span chain "
            "(ws→pg→redis→push) in trace-export.json."
        ),
        risk="Without a verifiable trace chain, PR-2 observability requirement is not met",
    )


def main(argv: Sequence[str]) -> int:
    try:
        checks: List[CheckResult] = []
        checks.append(_check_token_evidence())

        # Only attempt trace check when token evidence passes; otherwise it tends to cascade.
        if checks[-1].ok:
            checks.append(_check_trace_chain())
        else:
            checks.append(
                CheckResult(
                    name="Trace chain evidence",
                    ok=False,
                    conclusion="FAIL",
                    evidence="Skipped because token evidence failed",
                    risk="Trace evidence cannot be trusted without basic correlation tokens",
                )
            )

        overall_ok = all(c.ok for c in checks)
        _write_evidence(checks=checks, overall_ok=overall_ok)

        if overall_ok:
            print("Observability Gate PASSED")
            print(f"Evidence written: {TRACE_EVIDENCE_PATH}")
            return 0

        print("Observability Gate FAILED:", file=sys.stderr)
        for c in checks:
            if not c.ok:
                print(f"- {c.name}: {c.evidence}", file=sys.stderr)
        print(f"\nSee evidence: {TRACE_EVIDENCE_PATH}", file=sys.stderr)
        return 2

    except Exception as e:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            _write_evidence(
                checks=[
                    CheckResult(
                        name="runtime",
                        ok=False,
                        conclusion="FAIL",
                        evidence=str(e),
                        risk="Gate runtime error; observability evidence may be missing",
                    )
                ],
                overall_ok=False,
            )
        except Exception:
            pass

        print(f"Observability Gate runtime error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
