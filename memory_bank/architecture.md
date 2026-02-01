# architecture.md

## 0) 本文件的定位（v0 基线）

本文件是本仓库的“架构锚点 / 变更联动说明”，用于让 `memory_bank/implementation-plan.md` 的 Gate 2.1/2.2 可执行：

- 作为 PR 必读文档之一（Preflight 必读确认）。
- 当 PR 命中架构联动触发路径（见 `implementation-plan.md` 的 0.5）时，必须同步更新本文档，保证变更可追溯。

> 说明：仓库已进入 PR-2 MVP 可运行阶段，因此本文档补齐运行时架构中“事件存储按 class_session_id 分区”的策略与回滚/清理方案。

---

## 1) `memory_bank/` 内各文件的作用（面向协作与门禁）

### 1.1 `memory_bank/implementation-plan.md`
- 作用：CI 自动门禁规则的权威来源（7 个 Gate + 失败条件 + artifact 证据要求）。
- 维护者：所有向主分支合入代码的人；规则变更必须可审计。
- 与本文文件关系：
  - Gate 2.2 要求：命中触发路径时必须更新 `architecture.md`。
  - Gate 6/8 等要求的“最小链路”“干净环境复现”最终会在本文档补充更细的结构化说明。

### 1.2 `memory_bank/jishuzhan.md`
- 作用：技术栈建议（Flutter + NestJS + FastAPI + PG/Redis/BullMQ/OTel 等），用于团队对齐默认选型。
- 注意：如与 `implementation-plan.md` 的硬性门禁冲突，以门禁为准。

### 1.3 `memory_bank/双向个性化课堂管理AI App 产品需求与方案生成器 v1.0.0.md`
- 作用：产品/需求口径与方案生成提示词。

### 1.4 `memory_bank/progress.md`
- 作用：项目执行日志（每一步做了什么、为什么、如何验证、阻塞点）。

---

## 2) CI 门禁与架构联动的“落点”说明（v0）

### 2.1 架构联动触发（Gate 2.2）
当 PR 改动命中以下触发路径时，必须更新本文档（规则来源：`implementation-plan.md` 0.5）：

- `**/migrations/**`（DB/Schema）
- `**/openapi*.yml|yaml|json`（API 契约）
- `**/jobs/**`（异步任务）

### 2.2 可观测关联口径（Gate 6）
本仓库统一的关联口径（规则来源：`implementation-plan.md` 0.6）：

- HTTP Header：`x-correlation-id`
- 日志字段：`correlation_id`

---

## 3) PR-2 MVP：事件存储（PostgreSQL）按 `class_session_id` 分区/索引/保留/回滚策略

本节对应 PR-2 验收中的“PostgreSQL 必须可按 class_session_id 查询事件明细”以及“按 class_session_id 分区”的说明要求。

### 3.1 数据模型（核心表）
- `ClassSession`：课堂会话（服务端生成 `class_session_id`）。
- `ClassEvent`：事件明细（目前唯一事件类型：`class_enter`），字段包含：
  - `classSessionId`（= `class_session_id`，查询主键）
  - `userId`、`role`、`classId`
  - `eventType`（固定 `class_enter`）
  - `createdAt`、可选 `correlationId`

实现约束：事件写入后必须能通过 `class_session_id` 在 PG 中查询到对应记录。

### 3.2 “按 class_session_id 分区”的策略（MVP 版本：逻辑分区 + 索引保障）
MVP 阶段先采用“逻辑分区”的方式：
- 业务上所有事件查询、回放与排障都以 `class_session_id` 为主过滤条件（等价于分区键）。
- 数据库层通过复合索引确保按 `class_session_id` 的检索成本可控。

原因：
- 真正的 PG 原生分区（PARTITION BY）需要更重的 DDL 与迁移管理，并对查询计划与维护产生额外复杂度。
- PR-2 的目标是先把主链路在干净环境跑通并可审计；因此优先保证“可查、可回滚、可清理”。

> 后续演进：当单表规模增长到影响查询/清理（例如千万级）时，再从逻辑分区升级为 PG 原生分区（可按 `hash(class_session_id)` 或基于时间+session 的组合）。

### 3.3 索引策略
当前必须具备（见 `apps/api/prisma/schema.prisma` 与迁移脚本）：
- `ClassEvent(classSessionId, createdAt)`：保证按 `class_session_id` 查询该 session 内的事件序列。
- `ClassEvent(eventType, createdAt)`：保证按事件类型的运维/统计。
- `ClassSession(classId)`：便于按班级维度查询会话。

对 PR-2 而言，关键索引是：`(classSessionId, createdAt)`。

### 3.4 保留/清理计划（Retention & Cleanup）
MVP 保留策略（可审计且可执行）：
- 保留窗口：默认 30 天（可通过后续配置化）。
- 清理方式：按 `createdAt` 扫描并删除过期 `ClassEvent`；必要时再删除无事件且过期的 `ClassSession`。
- 执行机制：MVP 阶段允许人工/脚本触发；后续可引入定时任务（job）并纳入 CI 的架构联动门禁。

清理安全措施：
- 删除以 `createdAt < cutoff` 为主条件，避免误删当前活跃 session。
- 清理脚本必须输出被删除的 session/event 数量，并记录到可观测日志（含 correlation_id）。

### 3.5 失败回滚与修复策略（Failure rollback / repair）
典型失败点：
- PG 写入失败（Prisma create 抛错）
- Redis 聚合更新失败
- WS push 失败（连接断开/广播失败）

策略（MVP）：
1) 以“事件明细”为系统事实来源：
   - 如果 PG 写入失败：必须返回 `ack(ok=false)`，并且不得更新 Redis 聚合。
   - 如果 PG 写入成功但 Redis 更新失败：返回 `ack(ok=false)` 或记录错误；并允许后续通过“重算聚合”修复。
2) 聚合可重建：
   - 重建方式：对指定 `class_session_id` 扫描 `ClassEvent where classSessionId=... and eventType='class_enter'` 计数，然后覆盖写入 Redis。
   - MVP 阶段可提供内部脚本/运维手段（不要求对外 API）。
3) 回滚原则：
   - 不做跨 PG/Redis 的分布式事务。
   - 保证写入顺序：先 PG（事实）→ 后 Redis（缓存/聚合）→ 再 WS push。

---

## 4) 未來需要补齐的运行时架构目录
（略，后续随模块扩展再补充。）
