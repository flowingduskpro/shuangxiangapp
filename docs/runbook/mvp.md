# MVP Runbook

## Docker Compose quickstart

This repo provides a Docker Compose baseline per `memory_bank/implementation-plan.md` section 0.7:
Postgres + Redis + API.

Commands:
- `docker compose -f compose.yml up -d --build`
- `docker compose -f compose.yml logs -f api`
- `docker compose -f compose.yml down -v`

## Smoke test

MVP smoke for PR-2 is WS-based and will be driven by the e2e runner (see `artifacts/runbook/repro-steps.md`).

## Backward compatibility / 向后兼容策略（若涉及数据变更）

- If migrations are introduced, follow an expand/contract strategy.
- Rollback guidance must describe whether migrations can be rolled back safely and how.

## Rollback / 回滚方式

- `docker compose -f compose.yml down -v` (purges local volumes; for MVP only)
- For DB schema rollback: use expand/contract migrations; do not drop columns in the same PR that introduced them.
