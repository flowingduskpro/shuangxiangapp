# progress.md

## 2026-02-01 — Step 1（文档基线落地：让 Gate 2.1/2.2 可执行）

### 做了什么
- 补齐 `memory_bank/architecture.md`（v0）：
  - 明确 `memory_bank/` 各文档文件的职责与维护方式。
  - 写清楚门禁落点：
    - Gate 2.2 架构联动触发路径（migrations/openapi/jobs）变更必须更新本文件。
    - Gate 6 correlation 规范：`x-correlation-id` / `correlation_id`。
    - Gate 7 MVP scope 配置落点：`ci/mvp-scope-rules.yml`。

### 为什么这样做
- `memory_bank/implementation-plan.md` 将 `architecture.md` 作为 Preflight 必读与架构联动目标，但原文件为空会导致 Gate 2.1/2.2 无法形成一致口径与可审计记录。
- 本步先形成“可引用/可更新”的最小基线，为后续真实代码、目录、契约、数据流的落地提供锚点。

### 验证方式
- 本步仅涉及文档与配置，不引入业务代码。
- 等待你在本地跑现有检查/测试并确认通过。

### 约束
- 在你确认测试/检查通过前，不开始 Step 2。

