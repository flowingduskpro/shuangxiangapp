# artifacts/ (PR evidence tree)

This directory is reserved for **PR evidence artifacts** (auditable, reproducible).

Source of truth: `memory_bank/ShuangxiangApp AI roles.md` section **J**.

## PR-1 minimum requirement
PR-1 must produce (at least) the following files (they may be placeholders during early-repo phase):

- `artifacts/runbook/repro-steps.md`
- `artifacts/runbook/versions.txt`
- `artifacts/audit/dependency-integrity-report.md`
- `artifacts/audit/report-validation-result.json`
- `artifacts/audit/report-validation-log.txt`

## Notes
- CI also produces `ci_artifacts/` (gate script outputs). Those are uploaded separately.
- Future iterations will tighten the validations so these files contain real evidence, not placeholders.

