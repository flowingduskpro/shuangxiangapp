#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local smoke runner for PR-2.

This is a best-effort local runner to execute the real E2E chain and produce:
- artifacts/tests/e2e-ws-report.txt
- artifacts/observability/trace-export.json (real)

CI may use docker-compose or other orchestration; this script is mainly for
repro and to keep a single command for PR description.

Requirements (local):
- PostgreSQL running and DATABASE_URL pointing to it
- Redis running and REDIS_URL pointing to it
- Node deps installed (npm ci) and Prisma client generated

It starts the API as a subprocess with PR2_TRACE_EXPORT_PATH enabled.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ART = REPO_ROOT / "artifacts"


def _env_for_api() -> dict:
    env = dict(os.environ)
    env.setdefault("PORT", "3000")
    env.setdefault("JWT_SECRET", "dev-secret")
    env.setdefault("PR2_TRACE_EXPORT_PATH", str(ART / "observability" / "trace-export.json"))
    return env


def main() -> int:
    api_dir = REPO_ROOT / "apps" / "api"
    if not api_dir.exists():
        raise RuntimeError(f"missing api dir: {api_dir}")

    # Ensure artifacts skeleton exists
    (ART / "observability").mkdir(parents=True, exist_ok=True)
    (ART / "tests").mkdir(parents=True, exist_ok=True)

    # Build API to dist/ so we can run node dist/main.js
    subprocess.check_call(["npm", "run", "prisma:generate"], cwd=str(api_dir))
    subprocess.check_call(["npm", "run", "build"], cwd=str(api_dir))

    api = subprocess.Popen(
        ["node", "dist/main.js"],
        cwd=str(api_dir),
        env=_env_for_api(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        # wait for port bind (best-effort)
        time.sleep(1.0)

        e2e = subprocess.run(["python", str(REPO_ROOT / "ci" / "scripts" / "run_pr2_e2e_ws.py")], cwd=str(REPO_ROOT))
        return e2e.returncode

    finally:
        try:
            api.send_signal(signal.SIGINT)
            api.wait(timeout=5)
        except Exception:
            api.kill()

        # dump server logs to artifacts for debugging
        log_path = ART / "observability" / "api-local-stdout.log"
        try:
            out = ""
            if api.stdout:
                out = api.stdout.read()[:200000]
            log_path.write_text(out, encoding="utf-8")
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

