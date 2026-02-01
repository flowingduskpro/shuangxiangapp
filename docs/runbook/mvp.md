# MVP Runbook

## Docker Compose quickstart

> This repo is still bootstrapping. When runtime services land, add a Docker Compose baseline per
> `memory_bank/implementation-plan.md` section 0.7:
> Postgres + Redis + API + AI(FastAPI) + smoke script.

Planned commands (to be implemented once compose exists):
- `docker compose up -d`

## Smoke test

Planned smoke (to be implemented once services exist):
- `curl -H "x-correlation-id: <uuid>" http://localhost:<port>/health`

## Backward compatibility / 向后兼容策略（若涉及数据变更）

- If migrations are introduced, follow an expand/contract strategy.
- Rollback guidance must describe whether migrations can be rolled back safely and how.

## Rollback / 回滚方式

- Document rollback steps here (commands + any data implications).

