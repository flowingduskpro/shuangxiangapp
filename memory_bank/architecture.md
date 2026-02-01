# architecture.md

## 0) 本文件的定位（v0 基线）

本文件是本仓库的“架构锚点 / 变更联动说明”，用于让 `memory_bank/implementation-plan.md` 的 Gate 2.1/2.2 可执行：

- 作为 PR 必读文档之一（Preflight 必读确认）。
- 当 PR 命中架构联动触发路径（见 `implementation-plan.md` 的 0.5）时，必须同步更新本文件，保证变更可追溯。

> 现阶段（代码尚未落地/目录尚未建立），本文件先提供“文档级架构”与“门禁落点”；后续随着服务与模块成形，再补充运行时架构（模块边界、数据流、契约、合规与保留策略）。

---

## 1) `memory_bank/` 内各文件的作用（面向协作与门禁）

### 1.1 `memory_bank/implementation-plan.md`
- 作用：CI 自动门禁规则的权威来源（7 个 Gate + 失败条件 + artifact 证据要求）。
- 维护者：所有向主分支合入代码的人；规则变更必须可审计。
- 与本文件关系：
  - Gate 2.2 要求：命中触发路径时必须更新 `architecture.md`。
  - Gate 6/8 等要求的“最小链路”“干净环境复现”最终会在本文件补充更细的结构化说明（当前先由规则文件描述）。

### 1.2 `memory_bank/jishuzhan.md`
- 作用：技术栈建议（Flutter + NestJS + FastAPI + PG/Redis/BullMQ/OTel 等），用于团队对齐默认选型。
- 注意：如与 `implementation-plan.md` 的硬性门禁冲突，以门禁为准。

### 1.3 `memory_bank/双向个性化课堂管理AI App 产品需求与方案生成器 v1.0.0.md`
- 作用：产品/需求口径与方案生成提示词（等同门禁语境中的“@game-design-document”）。
- 典型用途：
  - 作为功能拆解、事件埋点、判定逻辑（退出/切屏/无操作）、推荐与反馈闭环的需求来源。

### 1.4 `memory_bank/progress.md`
- 作用：项目执行日志（每一步做了什么、为什么、如何验证、阻塞点）。
- 维护方式：按日期或步骤追加；用于后续开发者快速接手。

---

## 2) CI 门禁与架构联动的“落点”说明（v0）

### 2.1 架构联动触发（Gate 2.2）
当 PR 改动命中以下触发路径时，必须更新本文件（规则来源：`implementation-plan.md` 0.5）：

- `**/migrations/**`（DB/Schema）
- `**/openapi*.yml|yaml|json`（API 契约）
- `**/jobs/**`（异步任务）

本文件在后续版本需要补齐的对应内容：
- 数据模型/核心表与保留清理策略
- API/WS 契约版本与向后兼容策略
- 作业（job）输入输出、幂等键、重试/死信策略

### 2.2 可观测关联口径（Gate 6）
本仓库统一的关联口径（规则来源：`implementation-plan.md` 0.6）：

- HTTP Header：`x-correlation-id`
- 日志字段：`correlation_id`

后续当实现落地时，本文件将补充：
- correlation id 在客户端/服务端/队列任务中的传递规则
- trace/log 的最小字段集与脱敏口径

### 2.3 MVP Scope 规则落点（Gate 7）
- MVP 阶段的自动判定采用“关键词黑名单 hard fail”。
- 配置文件：`ci/mvp-scope-rules.yml`（可审计、可逐步补全）。

---

## 3) 未来需要补齐的运行时架构目录（待代码出现后更新）

当代码目录出现后，本文件将补齐：

- 单仓目录结构（例如 apps/services 的划分）与每个目录职责
- 模块边界与 import 约束（对应 Gate 3.3）
- 端到端数据流：客户端事件 → API → PostgreSQL/Redis →（可选）BullMQ → 结果产物
- AI 服务（FastAPI）在 MVP 中的必需链路与契约（输入/输出 schemas）
- 合规与保留策略：事件数据、日志、模型输入输出的保留周期与脱敏策略

