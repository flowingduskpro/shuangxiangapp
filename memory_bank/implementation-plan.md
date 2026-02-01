implementation-plan

# CI 自动门禁规则体系（v1.1，最终定稿）

## 0) 约定与默认口径（本仓库强制）

### 0.1 CI 平台与产物（artifact）

- CI 平台：GitHub Actions
- 产物目录（仓库内相对路径）：`ci_artifacts/`
- artifact 保留：30 天
- 固定产物文件名（至少包含以下 3 个，且路径固定）：
  - `ci_artifacts/structure-report.json`
  - `ci_artifacts/dependency-audit.md`
  - `ci_artifacts/trace-evidence.md`

> 规则原则：所有 Gate 的结论必须可复现、可追溯；CI 失败必须能从 artifact 直接定位到“具体文件/具体 import/具体步骤/具体证据”。

### 0.2 仓库形态（单仓）

- 本项目为单仓（monorepo）。
- 语言/栈范围：Flutter(Dart) + NestJS(TypeScript) + FastAPI(Python)。

### 0.3 必读文档映射（Preflight）

- `memory-bank/@architecture.md`：即 `memory_bank/architecture.md`（当前可能为空，后续追加基线；Preflight 仍要求“已阅读/知悉将补齐”）
- `memory-bank/@game-design-document.md`：指 `memory_bank/双向个性化课堂管理AI App 产品需求与方案生成器 v1.0.0.md`

### 0.4 统计口径：业务源代码/排除项/白名单

- 仅统计业务源代码后缀：`*.dart`、`*.ts`、`*.py`
- 排除（不参与行数统计与结构门禁的“生成/构建产物、声明、编译输出”）：
  - `**/generated/**`
  - `**/build/**`
  - `**/dist/**`
  - `**/*.g.dart`
  - `**/*.d.ts`
  - `**/*.pb.*`
- 行数白名单（允许超过阈值必须登记、可审计）：`ci/line-limit-whitelist.json`（每项必须含：path、reason、expires_at）

### 0.5 架构联动（2.2）的路径触发规则（近似自动化，先落地）

当 PR 改动命中下列任一“触发路径/文件模式”时，必须同时修改 `memory_bank/architecture.md`：

- DB/Schema：`**/migrations/**`
- API 契约：`**/openapi*.yml`、`**/openapi*.yaml`、`**/openapi*.json`
- 异步任务：`**/jobs/**`

> 可扩展：后续可按项目实际目录补充 `queues/`、`gateway/`、`routers/` 等，但本版本至少保证上述三类可自动触发。

### 0.6 端到端链路与可观测约束（固定 MVP 链路）

- 标准链路（MVP 至少 1 条，且必须可复现）：
  - 客户端事件 → 服务端接收 → PostgreSQL 写入 → Redis 聚合（如涉及）→（可选）BullMQ 任务 → 结果产物
- 关联要求：必须能通过 correlation id / trace id 串联上述链路（日志/trace/DB 事件记录至少二选一具备可验证证据）。

补充：本仓库 correlation 口径固定如下（所有端一致）：

- HTTP Header：`x-correlation-id`
- 日志字段：`correlation_id`

### 0.7 MVP 可复现运行基线

- 基线：Docker Compose
- 最小依赖：Postgres + Redis + API + AI(FastAPI) + smoke script
- AI 服务在 MVP 阶段为必须（不可用 stub 替代）。

------

## 1) CI 总体门禁（Always）

CI 必须包含并依序执行 7 个 Gate；任一 Gate 失败则流水线失败，禁止合并：

1. **Preflight Gate**（必读确认 + 架构更新联动）
2. **Structure Gate**（反 monolith：行数/文件数/边界）
3. **依赖完整复用审计** （依赖完整复用审计：1–40）
4. **Tests Gate**（自动化测试）
5. **可观测证据门** （可观测证据：trace/log/metrics）
6. **MVP Scope Gate**（范围控制：只做 MVP）
7. **Release Readiness Gate（最小发布就绪）**（版本/回滚/变更记录）

> 所有 Gate 的输出必须可复现、可追溯，并存档为 CI artifact（见 0.1）。不得给出模糊结论或主观推测。

------

## 2) 预检门（始终）

### 2.1 写代码前必读确认（硬要求）

PR 必须包含“必读确认记录”，并明确：

- 已阅读 `memory_bank/architecture.md`
- 已阅读 `memory_bank/双向个性化课堂管理AI App 产品需求与方案生成器 v1.0.0.md`
- 本次涉及的业务域（内容/课堂/监测/反馈/推荐/评分督导）
- 本次是否涉及：DB/事件契约/权限/保留策略/合规策略变更

**失败条件**

- PR 触及核心实现（任一域的业务逻辑、数据结构、接口、事件字段、任务队列、WS）但缺少必读确认记录。

### 2.2 架构更新联动（里程碑强制）

当 PR 引入以下任一变更时，必须同时更新 `memory_bank/architecture.md`：

- 新/改核心表、索引、分区策略、保留/清理策略
- 新/改事件字段或事件类型
- 新/改 API/WS 契约
- 新/改 BullMQ job（输入输出、幂等键、重试/死信）
- 新/改 Redis 聚合口径
- 新/改 AI 服务（FastAPI）输入输出契约
- 新/改权限边界、脱敏/匿名化策略

并且：当 PR 改动命中 0.5 的“路径触发规则”时，视为必须联动更新。

**失败条件**

- 有上述变更但 `memory_bank/architecture.md` 未改动
- `memory_bank/architecture.md` 改动但缺少：模块边界、数据流、契约、合规与保留策略说明

------

## 3) 结构门：反单体（始终）

### 3.1 单文件行数硬阈值（Always）

- 任一业务源代码文件（见 0.4）**> 250 行**：CI 失败
  （生成物/锁文件等可豁免，但必须进入白名单 `ci/line-limit-whitelist.json` 且可审计）

### 3.2 单业务域目录文件数硬阈值（Always）

- Flutter（Dart）/ NestJS（TS）：单域目录**同一层级**文件数 > **25**：失败
- FastAPI（Python）：单域目录同一层级文件数 > **20**：失败

### 3.3 边界与职责混杂检查（Always）

本项目采用“目录分层 + import 约束”作为机器规则（以稳定、可解释为第一优先级）：

- CI 必须自动检测并报告：
  - 分层目录之间的非法依赖（逆向 import / 跨域绕过契约层）→ 失败
  - 跨业务域直接依赖内部实现（绕过契约层）→ 失败

**CI artifact 必须包含**

- 超阈值文件清单（路径、行数、归属域）→ 写入 `ci_artifacts/structure-report.json`
- 超阈值目录清单（路径、文件数、拆分建议归类）→ 写入 `ci_artifacts/structure-report.json`
- 违规依赖链路证据（A 导入 B 的具体路径/引用点）→ 写入 `ci_artifacts/structure-report.json`

------

## 4) Dependency Integrity Gate：依赖完整复用审计（Always，覆盖你的 1–40 条）

> 说明：1–40 条要求已融入本文件，CI 严格以本文件为准；不得额外引入口径外的“主观解释”。

### 4.1 逐条审计输出格式（强制）

CI 必须生成并存档《依赖完整性审计报告》：`ci_artifacts/dependency-audit.md`，对关键依赖逐条输出：

- 结论：满足 / 不满足 / 不适用
- 证据：必须可验证（版本、来源、路径解析、运行期加载证明、调用证明）
- 风险后果：若不满足会导致什么偏差（行为漂移、合规、稳定性、审计不可通过）

**禁止**

- 模糊判断、主观推测

### 4.2 来源/版本锁定（强制可复现）

CI 必须输出并存档：

- Flutter：依赖解析后的版本清单
- Node：安装后的包版本清单（与 lockfile 一致）
- Python：可复现安装清单（锁定版本或等效机制）

**失败条件**

- 发现复制依赖源代码进当前项目并修改使用
- 发现裁剪/重写/降级封装依赖库功能
- 发现 mock/stub/demo/占位实现承担真实功能
- 发现“只导入不用”的伪集成

### 4.3 运行期加载路径证明（强制）

必须证明运行期加载的是**目标公开依赖的完整实现**，并排除：路径遮蔽、重名模块、隐式 fallback。

**失败条件**

- 任何关键依赖在运行期未参与执行
- 任何关键能力由替代/简化实现承担

------

## 5) Tests Gate：每一步必须有测试（Always）

### 5.1 MVP 最低测试门槛（必须满足）

- Flutter：在 Android emulator 里跑 `integration_test`，并产出时间阈值证据（JSON）
  - 退出阈值：≥10s
  - 切屏阈值：≥5s
  - 无操作阈值：≥3min
  - 证据文件建议：写入 `ci_artifacts/flutter-perf-evidence.json`
- NestJS：鉴权/越权/字段校验的契约或集成测试必须存在（默认 jest + supertest）
- FastAPI：OCR/抽取/推荐任一涉及部分必须有回归样本测试（pytest + golden set）

### 5.2 边界用例（涉及即必须测）

- 断网/弱网：离线缓存 → 恢复补传 → 幂等去重
- 杀后台：退出判定正确
- 并发：100 人/课堂聚合口径正确（至少提供可复现并发模拟/压测）

**失败条件**

- 有行为变更但无相应测试或无测试说明
- 测试不稳定且无隔离策略说明

------

## 6) Observability Gate：最小可观测证据（Always）

为满足“审计必须基于可验证证据”，每个 PR 必须产出最小链路证据（artifact 或日志片段）。

### 6.1 必须覆盖的最小链路

至少 1 条端到端链路（MVP 范围内），固定链路见 0.6。

### 6.2 必须可关联

- 必须能用 correlation id / trace id（或等效机制）把链路串起来
- 日志/trace 中必须出现可审计关键字段（如 class_session_id 等），并按合规要求脱敏

证据必须写入：`ci_artifacts/trace-evidence.md`

**失败条件**

- 不能证明关键依赖在运行期真实执行
- 无法关联链路、证据不可复现、或证据依赖人工主观判断

------

## 7) MVP 范围门：范围控制（始终）

MVP 阶段禁止进入主分支：

- 摄像头监控、MDM 强控、自动惩戒扣分
- V1/V2 的复杂模型（embedding/协同过滤/个性化排序等）
- 将 OCR/抽取/推荐算法实现塞进 NestJS（必须在 FastAPI）

**失败条件**

- 发现超范围目录/模块/功能进入（由变更清单 + 架构对照 + 可审计规则判定）

补充：MVP Scope 的自动判定采用“关键词黑名单 hard fail”（可审计配置）——命中即失败：

- 规则文件：`ci/mvp-scope-rules.yml`
- 默认策略：对改动文件的路径与内容做关键词匹配；命中即 CI 失败

------

## 8) 发布就绪门：最小发布就绪（始终）

每个可合并 PR 必须具备：

- 变更记录（影响范围、回滚方式）
- 数据变更的向后兼容策略（若有）
- 最小运行说明：如何在干净环境跑通最小链路（Docker Compose；见 0.7）

**失败条件**

- 不能说明回滚或升级路径
- 不能在干净环境复现最小链路

------

# 9) 最终补充：对“模块化”与“依赖黑箱”的统一口径（Always）

- **模块化**指：业务域拆分 + 流程拆分 + 测试可独立运行
- **不得二次抽象**指：不得把成熟库再包成自研通用层；不得重写库能力
- 当前项目只写：业务编排、模块组合、参数配置、IO 适配
- 任何通用能力必须来自成熟依赖，且必须能通过“依赖完整性审计 + 可观测证据”证明其真实执行