# ci-report-validation-rules.md

PR-2 standard artifact directory list (Always, fixed names).

Missing any item MUST fail CI.

## J1. Audit reports
- artifacts/audit/dependency-integrity-report.md
- artifacts/audit/report-validation-result.json
- artifacts/audit/report-validation-log.txt

## J2. Dependency versions & resolve paths
### Flutter
- artifacts/deps/flutter/pub-resolved.txt
- artifacts/deps/flutter/pub-sources.txt
- artifacts/deps/flutter/package-resolve-paths.txt

### Node/NestJS
- artifacts/deps/node/node-resolved.txt
- artifacts/deps/node/node-sources.txt
- artifacts/deps/node/node-resolve-paths.txt

### Python
- artifacts/deps/python/python-deps-status.txt

## J3. Shadowing / duplicate module checks
- artifacts/security/shadowing-check.txt
- artifacts/security/duplicate-module-names.txt

## J4. Static checks (unused imports / false integration)
- artifacts/static/ununsed-imports.txt
- artifacts/static/false-integration-check.txt

## J5. Test reports
- artifacts/tests/flutter-test-report.txt
- artifacts/tests/nest-test-report.txt
- artifacts/tests/e2e-ws-report.txt

## J6. Observability evidence
- artifacts/observability/trace-export.json
- artifacts/observability/correlation-ids.txt
- artifacts/observability/service-logs.txt
- artifacts/observability/e2e-timeline.txt

## J7. Runbook & reproduction info
- artifacts/runbook/repro-steps.md
- artifacts/runbook/versions.txt

