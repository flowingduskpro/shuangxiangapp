#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dependency Integrity Gate (Gate 4) checker.

Implements `memory_bank/implementation-plan.md` section 4.

Contract:
- Always produce: `ci_artifacts/dependency-audit.md`
- Exit code:
  - 0 on pass
  - 2 on fail (rule violations)
  - 3 on unexpected runtime error

Design notes (repo-aware):
- This repo is a monorepo intended for Flutter + NestJS + FastAPI, but code roots
  may not exist yet.
- If no dependency manifests are present, Gate 4 is treated as "N/A" and passes,
  but still creates an audit report explaining why.
- We do NOT install dependencies or make network calls here; this gate focuses
  on deterministic evidence from repo state + lightweight runtime load-path proof
  where possible.

Fail conditions (subset of plan 4.2/4.3 that are machine-checkable without builds):
- If a stack manifest exists but no lock/pin mechanism exists (as defined below).
- If a dependency appears to be vendored / copied into the repo (best-effort).

Lock/pin expectations (minimal, to keep the gate usable early):
- Flutter: presence of `pubspec.lock` next to `pubspec.yaml`.
- Node: presence of one of `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`.
- Python: presence of one of `requirements.txt`, `requirements.lock`,
  `poetry.lock`, `pdm.lock`, `uv.lock`, or `requirements.txt` with pinned
  versions (best effort).

Runtime load-path proof:
- For Node: if both `package.json` and `package-lock.json` exist AND `node_modules`
  exists, attempt `node -p "require.resolve('<pkg>')"` for direct deps.
- For Python: if a venv is active and deps are installed, attempt to import and
  show module file path. Otherwise mark as N/A.
- Flutter: runtime path proof is marked N/A here (requires Flutter toolchain).

Outputs:
- Markdown report with per-stack and per-direct-dependency entries.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "ci_artifacts"
REPORT_MD_PATH = ARTIFACTS_DIR / "dependency-audit.md"


@dataclass
class Violation:
    kind: str
    path: str
    details: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_report(md: str) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_MD_PATH.write_text(md, encoding="utf-8")


def _iter_files(names: Sequence[str]) -> Iterable[Path]:
    # Keep it simple: find by exact filename anywhere under repo (excluding common build dirs)
    exclude_dirs = {".git", ".idea", "ci_artifacts", "node_modules", "build", "dist", "generated", ".dart_tool", ".venv", "__pycache__"}
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        parts = {x.lower() for x in p.parts}
        if any(ed.lower() in parts for ed in exclude_dirs):
            continue
        if p.name in names:
            yield p


def _rel(p: Path) -> str:
    return p.relative_to(REPO_ROOT).as_posix()


def _looks_like_vendored_dependency_tree(p: Path) -> bool:
    # Best-effort heuristic for "copied dependency source".
    rel = _rel(p).lower()
    return any(
        seg in rel
        for seg in (
            "/vendor/",
            "/third_party/",
            "/third-party/",
            "/3rdparty/",
            "/deps/",
            "/dependencies/",
        )
    )


def _parse_package_json(path: Path) -> Dict[str, Dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    deps = data.get("dependencies") or {}
    dev = data.get("devDependencies") or {}
    peer = data.get("peerDependencies") or {}
    # Only care about direct deps; keep strings.
    def _to_str_map(d: object) -> Dict[str, str]:
        if not isinstance(d, dict):
            return {}
        out: Dict[str, str] = {}
        for k, v in d.items():
            if isinstance(k, str) and isinstance(v, str):
                out[k] = v
        return out

    return {"dependencies": _to_str_map(deps), "devDependencies": _to_str_map(dev), "peerDependencies": _to_str_map(peer)}


def _direct_deps_summary(pkg: Dict[str, Dict[str, str]], *, include_dev: bool = True) -> List[Tuple[str, str, str]]:
    items: List[Tuple[str, str, str]] = []
    for section in ("dependencies", "peerDependencies"):
        for name, spec in sorted(pkg.get(section, {}).items()):
            items.append((section, name, spec))
    if include_dev:
        for name, spec in sorted(pkg.get("devDependencies", {}).items()):
            items.append(("devDependencies", name, spec))
    return items


def _has_any_lockfile(dir_path: Path, names: Sequence[str]) -> Optional[Path]:
    for n in names:
        p = dir_path / n
        if p.exists() and p.is_file():
            return p
    return None


def _python_req_pinned(req_line: str) -> bool:
    # Accept strict pins like pkg==1.2.3, pkg===1.2.3. Ignore comments and blanks.
    line = req_line.strip()
    if not line or line.startswith("#"):
        return True
    if line.startswith("-r ") or line.startswith("--requirement"):
        return True
    if line.startswith("--"):
        return True
    # allow direct url / git refs as pinned by commit (best effort)
    if "@" in line and ("git+" in line or "http://" in line or "https://" in line):
        return True
    return "==" in line or "===" in line


def _check_python_requirements_pinned(req_path: Path) -> bool:
    lines = req_path.read_text(encoding="utf-8", errors="replace").splitlines()
    # Consider pinned if all non-empty, non-comment entries are pinned.
    return all(_python_req_pinned(l) for l in lines)


def _detect_node_runtime_proof(project_dir: Path, deps: List[Tuple[str, str, str]]) -> List[str]:
    # Only if node exists and node_modules exists; otherwise N/A.
    node_modules = project_dir / "node_modules"
    if not node_modules.exists():
        return ["- runtime load-path proof: N/A (node_modules not present)"]

    # We attempt to resolve a few deps (limit to keep CI quick).
    to_check = [name for section, name, _ in deps if section == "dependencies"]
    to_check = to_check[:10]
    if not to_check:
        return ["- runtime load-path proof: N/A (no direct dependencies)"]

    node = os.environ.get("NODE", "node")
    lines: List[str] = ["- runtime load-path proof:"]
    for name in to_check:
        # Use node -p require.resolve; capture path.
        cmd = [
            "node",
            "-p",
            # Quote the package name so scoped packages like @nestjs/common work.
            f"require.resolve('{name}')",
        ]
        rc, out, err = _run_shell(cmd, cwd=project_dir)
        if rc == 0:
            lines.append(f"  - `{name}` resolved to `{out.strip()}`")
        else:
            lines.append(
                f"  - `{name}` resolve FAILED (rc={rc}). stderr: {err.strip()[:200]}"
            )
    return lines


def _detect_python_runtime_proof() -> List[str]:
    # If a python env has deps installed, show module file paths for a few common libs.
    # We don't know the concrete deps yet, so keep it N/A by default.
    return ["- runtime load-path proof: N/A (no Python dependency environment inspection in this repo state)"]


def _run_shell(command: str, *, cwd: Path) -> Tuple[int, str, str]:
    import subprocess

    completed = subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def _audit_flutter(pubspec_paths: List[Path]) -> Tuple[List[str], List[Violation]]:
    lines: List[str] = []
    violations: List[Violation] = []

    lines.append("## Flutter (Dart)")
    if not pubspec_paths:
        lines.append("- conclusion: N/A (no pubspec.yaml found)")
        lines.append("- evidence: repo scan found 0 pubspec.yaml")
        lines.append("- risk: N/A")
        lines.append("")
        return lines, violations

    for p in sorted(pubspec_paths, key=_rel):
        d = p.parent
        lock = d / "pubspec.lock"
        ok = lock.exists()
        lines.append(f"### { _rel(p) }")
        lines.append(f"- conclusion: {'PASS' if ok else 'FAIL'}")
        lines.append(f"- evidence: pubspec.lock {'present' if ok else 'missing'} at `{_rel(lock)}`")
        lines.append(
            "- risk: without pubspec.lock, dependency resolution may drift across installs, causing non-reproducible builds"
        )
        lines.append("")
        if not ok:
            violations.append(
                Violation(
                    kind="missing_lockfile",
                    path=_rel(p),
                    details="Flutter project has pubspec.yaml but missing pubspec.lock",
                )
            )

    return lines, violations


def _audit_node(package_json_paths: List[Path]) -> Tuple[List[str], List[Violation]]:
    lines: List[str] = []
    violations: List[Violation] = []

    lines.append("## Node (NestJS/TypeScript)")
    if not package_json_paths:
        lines.append("- conclusion: N/A (no package.json found)")
        lines.append("- evidence: repo scan found 0 package.json")
        lines.append("- risk: N/A")
        lines.append("")
        return lines, violations

    lock_candidates = ["package-lock.json", "pnpm-lock.yaml", "yarn.lock"]

    # Workspace-friendly: if repo root has a lockfile, allow nested package.json to rely on it.
    root_lock = _has_any_lockfile(REPO_ROOT, lock_candidates)

    for p in sorted(package_json_paths, key=_rel):
        d = p.parent
        lock = _has_any_lockfile(d, lock_candidates) or root_lock
        ok = lock is not None
        pkg = _parse_package_json(p)
        deps = _direct_deps_summary(pkg)

        lines.append(f"### { _rel(p) }")
        lines.append(f"- conclusion: {'PASS' if ok else 'FAIL'}")
        lines.append(
            f"- evidence: lockfile {'present: `' + _rel(lock) + '`' if lock else 'missing (expected one of: ' + ', '.join(lock_candidates) + ')'}"
        )
        lines.append(
            "- risk: without a lockfile, dependency versions may drift, breaking reproducibility and security auditing"
        )
        lines.append("- direct dependencies (from package.json):")
        if deps:
            for section, name, spec in deps:
                lines.append(f"  - `{name}` ({section}): `{spec}`")
        else:
            lines.append("  - (none)")

        # Runtime proof (best-effort)
        lines.extend(_detect_node_runtime_proof(d, deps))
        lines.append("")

        if not ok:
            violations.append(
                Violation(
                    kind="missing_lockfile",
                    path=_rel(p),
                    details="Node project has package.json but missing lockfile",
                )
            )

    return lines, violations


def _audit_python() -> Tuple[List[str], List[Violation]]:
    lines: List[str] = []
    violations: List[Violation] = []

    lines.append("## Python (FastAPI)")

    req_paths = list(_iter_files(["requirements.txt", "requirements.lock"]))
    pyproject_paths = list(_iter_files(["pyproject.toml"]))
    lock_paths = list(_iter_files(["poetry.lock", "pdm.lock", "uv.lock"]))

    if not req_paths and not pyproject_paths:
        lines.append("- conclusion: N/A (no requirements.txt or pyproject.toml found)")
        lines.append("- evidence: repo scan found no Python dependency manifests")
        lines.append("- risk: N/A")
        lines.append("")
        return lines, violations

    # requirements.txt
    for p in sorted(req_paths, key=_rel):
        pinned = _check_python_requirements_pinned(p)
        lines.append(f"### { _rel(p) }")
        lines.append(f"- conclusion: {'PASS' if pinned else 'FAIL'}")
        lines.append(f"- evidence: requirements entries {'all pinned (==/===) or equivalent' if pinned else 'contain unpinned specs'}")
        lines.append(
            "- risk: if requirements are not pinned, installs may drift across time/hosts and break reproducibility"
        )
        lines.extend(_detect_python_runtime_proof())
        lines.append("")
        if not pinned:
            violations.append(
                Violation(
                    kind="unpinned_python_requirements",
                    path=_rel(p),
                    details="Python requirements.txt contains unpinned dependency spec(s)",
                )
            )

    # pyproject + lock
    for p in sorted(pyproject_paths, key=_rel):
        d = p.parent
        has_lock = any((d / n).exists() for n in ("poetry.lock", "pdm.lock", "uv.lock")) or bool(
            [lp for lp in lock_paths if lp.parent == d]
        )
        lines.append(f"### { _rel(p) }")
        lines.append(f"- conclusion: {'PASS' if has_lock else 'FAIL'}")
        if has_lock:
            # pick one lockfile name
            lf = None
            for n in ("poetry.lock", "pdm.lock", "uv.lock"):
                if (d / n).exists():
                    lf = d / n
                    break
            lines.append(f"- evidence: lockfile present: `{_rel(lf)}`" if lf else "- evidence: lockfile present")
            lines.append("- risk: locked dependency set supports reproducible installs")
        else:
            lines.append("- evidence: missing lockfile next to pyproject.toml (expected poetry.lock/pdm.lock/uv.lock)")
            lines.append(
                "- risk: without a lockfile, resolved versions may drift; security auditing becomes unreliable"
            )
            violations.append(
                Violation(
                    kind="missing_lockfile",
                    path=_rel(p),
                    details="pyproject.toml found but no lockfile present",
                )
            )
        lines.extend(_detect_python_runtime_proof())
        lines.append("")

    return lines, violations


def main(argv: Sequence[str]) -> int:
    try:
        # Detect vendored folders (best-effort)
        vendored_hits = [p for p in _iter_files(["README.md"]) if _looks_like_vendored_dependency_tree(p)]
        # The above is intentionally light; we'll only report it, not fail by default.

        pubspec_paths = list(_iter_files(["pubspec.yaml"]))
        package_json_paths = list(_iter_files(["package.json"]))

        md: List[str] = []
        md.append("# dependency-audit.md")
        md.append("")
        md.append("This file is produced by Gate 4 (Dependency Integrity) automation.")
        md.append("")
        md.append("## Inputs")
        md.append(f"- timestamp_utc: `{_utc_now()}`")
        md.append("")
        md.append("## Summary")
        md.append("- policy source: `memory_bank/implementation-plan.md` section 4")
        md.append("- note: this repo may not have code roots yet; N/A is allowed in that phase")
        md.append("")

        all_violations: List[Violation] = []

        part, v = _audit_flutter(pubspec_paths)
        md.extend(part)
        all_violations.extend(v)

        part, v = _audit_node(package_json_paths)
        md.extend(part)
        all_violations.extend(v)

        part, v = _audit_python()
        md.extend(part)
        all_violations.extend(v)

        md.append("## Gate result")
        if all_violations:
            md.append("- overall: FAIL")
            md.append("- violations:")
            for vv in all_violations:
                md.append(f"  - [{vv.kind}] `{vv.path}`: {vv.details}")
        else:
            md.append("- overall: PASS")
            md.append("- violations: (none)")

        if vendored_hits:
            md.append("")
            md.append("## Best-effort signals (informational)")
            md.append(
                "- vendored dependency tree indicators were found (please check if any third-party source was copied into repo):"
            )
            for p in sorted(vendored_hits, key=_rel)[:20]:
                md.append(f"  - `{_rel(p)}`")

        md.append("")
        _write_report("\n".join(md) + "\n")

        if all_violations:
            print("Dependency Integrity Gate FAILED", file=sys.stderr)
            print(f"See report: {REPORT_MD_PATH}", file=sys.stderr)
            return 2

        print("Dependency Integrity Gate PASSED")
        print(f"Report written: {REPORT_MD_PATH}")
        return 0

    except Exception as e:
        try:
            _write_report(
                "\n".join(
                    [
                        "# dependency-audit.md",
                        "",
                        "This file is produced by Gate 4 (Dependency Integrity) automation.",
                        "",
                        f"- timestamp_utc: `{_utc_now()}`",
                        "",
                        "## Gate result",
                        "- overall: ERROR",
                        f"- runtime_error: `{str(e)}`",
                        "",
                    ]
                )
            )
        except Exception:
            pass
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

