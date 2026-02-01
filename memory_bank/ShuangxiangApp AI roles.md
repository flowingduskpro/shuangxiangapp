# ShuangxiangApp AI 工程规则（最终定稿 v1.1）

> 目标：强制 **模块化（多文件）**，严禁 **单体巨文��（monolith）**；严格 **MVP 优先**；严格 **依赖完整复用成熟生产级库**（禁止复制/裁剪/重写/替代）；所有步骤 **小而具体** 且 **每步必须有测试**；所有结论必须 **可验证、可审计、可复现**。

---

## 0) 规则等级与优先级（Always）

### 0.1 规则等级
- **Always**：硬规则。不满足必须停止实现，先修复。
- **Guideline**：默认遵循。若偏离必须说明原因、影响、替代方案、回归测试。

### 0.2 冲突处理优先级（从高到低）
1. 合规 / 隐私 / 安全
2. Always：必读、里程碑更新、反 monolith、每步测试、CI 门禁
3. 依赖完整复用与完整性审计（��款 1–40）
4. 技术栈最佳实践（Flutter / NestJS / FastAPI / PG / Redis / BullMQ / WS / OTel）
5. 风格与偏好

### 0.3 “模块化”与“不得二次抽象依赖”的统一口径（Always）
- 允许并强制 **按业务域拆模块**、按用例拆流程，确保多文件、可测、可维护。
- 禁止把成熟依赖库再包成“自研通用层/框架层”（网络层、埋点 SDK、队列框架、状态框架等）。
- **允许拆分的内容仅限：业务流程编排、模块组合调度、参数配置、输入输出适配。**
- **禁止：复制依赖源码、裁剪、重写、降级封装、替代实现、伪集成。**

---

## A) 开工必读与里程碑更���（Always）

### A1. 写任何代码前必须完整阅读（Always）
写任何代码前必须完整阅读：
- `memory-bank/@architecture.md`（包含完整数据库结构）
- `memory-bank/@game-design-document.md`

并在开始实现前明确确认：
- DB 是否覆盖：课堂会话、事件埋点明细、反馈、知识点、推荐、评分/督导
- 事件契约是否覆盖并符合验收口径
- 权限边界是否明确：教师仅本班，学生仅个人+班级聚合

若上述文件缺失/空/不一致：必须先要求补齐或更新，禁止先写代码。

### A2. 每完成重大功能或里程碑后必须更新架构（Always）
每完成一个重大功能或里程碑后，必须更新 `memory-bank/@architecture.md`，至少包含：
- 模块边界（Flutter / NestJS / FastAPI / PG / Redis / WS / BullMQ / S3 / OTel）
- 数据结构变更（表/索引/分区/保留与清理）
- 事件与 WS/API 契约（字段、版本、兼容策略）
- 异步任务清单（BullMQ：幂等键、重试、死信、可观测）
- 合规策略（最小化采集、匿名化、保留周期）
- 可观测性字段规范（trace/correlation、日志字段、指标）

重大功能/里程碑包含但不限于：
- 新业务域上线：内容/课堂/监测/反馈/推荐/评分督导
- 引入或变更：WS、BullMQ、Redis 聚合、核心表/事件字段、权限边界、报表口径、AI 服务契约

---

## B) 反 monolith：强制模块化与硬阈值（Always）

### B1. 单文件行数硬阈值（Always）
任一业务源码文件 **> 250 行** 必须拆分，否则禁止继续。

### B2. 单业务域目录文件数硬阈值（Always）
单业务域目录 **同一层级**文件数不得超过：
- Flutter（Dart）：25
- NestJS（TypeScript）：25
- FastAPI（Python）：20

触发阈值必须立刻二级拆分，否则禁止继续新增功能。

### B3. 职责混杂与跨域耦合禁止（Always）
禁止单文件/单模块同时承担 2+ 层职责：
- UI、状态管理、业务规则、网络、存储、埋点、报表聚合、推荐算法

禁止单文件/单模块跨 2+ 业务域：
- 内容管理、课堂会话、专注监测、反馈闭环、推荐、评分督导

跨域交互必须通过：
- 明确的契约层（contracts）与域边界接口
禁止绕过契约层直接 import 对方内部实现。

### B4. 拆分方式（Always）
触发阈值或职责混杂时，按顺序拆分：
1) 按子能力二级目录拆分
2) 本域 contract 子目录集中声明（仅契约/字段/版本，不含逻辑）
3) usecase 子目录承载流程编排（每个用例对应最小流程）
4) infra-adapter 按依赖类型分（network/ws/db/queue/telemetry/storage），仅做 IO 适配，不得二次抽象成熟库能力

### B5. 结构验证（Always）
每一步必须通过：
- 文件行数审计
- 目录文件数审计
- 跨域依赖边界审计
- 每个业务域测试可独立运行

---

## C) 小步交付与测试（Always）

### C1. 每一步必须小而具体（Always）
每一步必须包含：
1) 目标（可验收）
2) 改动范围（模块/文件/边界）
3) 风险点（合规/误判/性能/一致性）
4) **测试**（自动化优先；否则提供可复现手测脚本+预期结果）
5) 回滚策略

### C2. 每一步必须有测试（Always）
不允许“后面再补测试”。
涉及到的边界条件必须测：
- 断网/弱网：离线→补传→幂等
- 杀后台：退出判定（后续迭代）
- 并发：100 人/课堂（在对应里程碑必须完成验证）

---

## D) 合规与 MVP 范围（Always）

### D1. 默认温和监管（Always）
默认策略：最小化采集 + 端侧判定 + 统计报表 + 教师确认。
MVP 禁止：
- 摄像头监控
- MDM 强制管控
- 自动惩戒扣分

### D2. 数据保留策略（Always）
必须在架构中明确并可验证：
- 行为数据：30 天游动保留（含清理机制/验证方法）
- 学习数据：学期结束保留（归档策略）
- 个人标识：匿名化/去标识（字段级策略）

---

## E) 技术栈规则（Guideline，默认遵循）

### E1. Flutter（单 App + 角色模式）
- 角色（teacher/student）仅影响：路由可见性、权限校验前置提示、功能开关；不得复制两套业务实现。
- 状态管理优先：Riverpod（或 Bloc 二选一，禁止两套并存）
- 网络：Dio（不得复制/改写其实现）
- 本地事件队列优先：Drift(SQLite)（用于离线补传与去重）
- 崩溃：Sentry；可观测：OTel（或等效）

### E2. NestJS（API/BFF + WS + BullMQ）
- WS Gateway 只做连接/鉴权/路由，业务逻辑下沉 usecase/service
- BullMQ：必须幂等、可观测、可重试、可死信
- Redis：只做课堂实时聚合，不做长期事实源
- PG：主库；行为事件明细 MVP 使用分区策略（本项目选择按 class_session_id 分区）

### E3. FastAPI（AI/内容处理）
- AI/OCR/抽取/推荐算法实现必须在 FastAPI，禁止塞进 NestJS
- LLM/OCR 必须有超时、降级、缓存与审计（后续迭代逐步引入）

---

## F) MVP 优先：从最小链路开始（Always）

基础框架完成的唯一判定（Always）：
- 必须跑通最小链路并通过 CI：
  `connect → auth → join_class_session → event(class_enter) → PG 写入 → Redis 聚合 → WS push(class_session_aggregate)`
- 必须产出可关联的 Observability 证据（trace/log），并在 CI artifact 中可复现定位。

---

## G) 依赖完整复用与审计约束（Always，原样纳入 1–40）

> 以下 1–40 条款必须逐条审计，逐条给出结论、证据、风险后果。任何情况下不得生成或补写依赖库内部实现代码。

1. 不得自行实现底层或通用逻辑，必须优先、直接、完整复用既有成熟仓库与生产级库  
2. 不得为了方便而复制依赖库代码到当前项目中再修改使用  
3. 不得对依赖库进行任何形式的功能裁剪、逻辑重写或降级封装  
4. 允许使用本地源码直连或包管理器安装方式，但实际加载的必须是完整生产级实现  
5. 不得使用简化版、替代版或重写版依赖冒充真实库实现  
6. 所有依赖路径必须真实存在并指向完整仓库源码  
7. 不得通过路径遮蔽、重名模块或隐式 fallback 加载非目标实现  
8. 代码中必须直接导入完整依赖模块，不得进行子集封装或二次抽象  
9. 不得在当前项目中实现依赖库已提供的同类功能  
10. 所有被调用能力必须来自依赖库的真实实现，不得使用 Mock、Stub 或 Demo 代码  
11. 不得存在占位实现、空逻辑或“先写接口后补实现”的情况  
12. 当前项目仅允许承担业务流程编排、模块组合调度、参数配置与输入输出适配职责  
13. 不得在当前项目中重复实现算法、数据结构或复杂核心逻辑  
14. 不得将依赖库中的复杂逻辑拆出后自行实现  
15. 所有导入的模块必须在运行期真实参与执行  
16. 不得存在“只导入不用”的伪集成行为  
17. 必须确保 sys.path 或依赖注入链路加载的是目标生产级本地库  
18. 不得因路径配置错误导致加载到裁剪版、测试版或简化实现  
19. 在生成代码时必须明确标注哪些功能来自外部依赖  
20. 在任何情况下不得生成或补写依赖库内部实现代码  
21. 只允许生成最小必要的胶水代码与业务层调度逻辑  
22. 必须假设依赖库为权威且不可修改的黑箱实现  
23. 项目评价标准以是否正确、完整站在成熟系统之上构建为唯一依据，而非代码量  

### 系统性代码与功能完整性检查约束
24. 不得允许任何形式的功能弱化、裁剪或替代实现通过审计  
25. 必须确认所有功能模块均为完整生产级实现  
26. 不得存在阉割逻辑、Mock、Stub 或 Demo 级替代代码  
27. 必须确保行为与生产环境成熟版本完全一致  
28. 必须验证当前工程是否 100% 复用既有成熟代码  
29. 不得存在任何形式的重新实现或功能折叠  
30. 必须确认当前工程为直接集成而非复制后修改  
31. 必须核查所有本地库导入路径真实、完��且生效  
32. 必须确认 datas 模块为完整数据模块而非子集  
33. 必须确认 sizi.summarys 为完整算法实现且未降级  
34. 不得允许参数简化、逻辑跳过或隐式行为改变  
35. 必须确认所有导入模块在运行期真实参与执行  
36. 不得存在接口空实现或导入不调用的伪集成  
37. 必须检查并排除路径遮蔽、重名模块误导加载问题  
38. 所有审计结论必须基于可验证的代码与路径分析  
39. 不得输出模糊判断或基于主观推测的结论  
40. 审计输出必须明确给出结论、逐项判断及风险后果  

---

## H) CI 七大 Gate（Always）

CI 必须分成 7 个 Gate，任一失败则禁止合并：
1. Preflight Gate（必读确认 + 架构联动）
2. Structure Gate（反 monolith：行数/文件数/边界）
3. Dependency Integrity Gate（1–40 逐条审计 + 报告校验）
4. Tests Gate（自动化测试必须通过）
5. Observability Gate（必须产出可关联证据）
6. MVP Scope Gate（禁止超范围功能）
7. Release Readiness Gate（可复现启动与回滚说明）

---

## I) Dependency Integrity Gate 的 CI 产物（Always）

### I1. 每个 PR 必须生成的审计报告（Always）
每个 PR 必须生成并上传 CI artifact：
- `dependency-integrity-report.md`：按 1–40 条逐项填写（结论/证据/风险后果）
- `report-validation-result.json`：报告校验结果（PASS/FAIL + 原因）

### I2. 全量逐条执行口径（Always）
- 每个 PR 必须 **全量覆盖 1–40**，不得缺项、不得跳号、不得合并条款。
- 任一适用条款“不满足” → CI 失败。
- 任一“不适用”条款必须写明：不适用原因 + 触发条件 + 验证方法，否则 CI 失败。
- 证据必须引用 CI artifact 中真实存在的文件/trace id/日志定位。

---

## J) PR-2 标准 artifact 目录清单（Always，固定命名）

> 用于保证证据可复现与自动校验稳定。缺一即 CI 失败。

### J1. 审计报告类
- `artifacts/audit/dependency-integrity-report.md`
- `artifacts/audit/report-validation-result.json`
- `artifacts/audit/report-validation-log.txt`

### J2. 依赖版本与解析路径类
- Flutter：
  - `artifacts/deps/flutter/pub-resolved.txt`
  - `artifacts/deps/flutter/pub-sources.txt`
  - `artifacts/deps/flutter/package-resolve-paths.txt`
- Node/NestJS：
  - `artifacts/deps/node/node-resolved.txt`
  - `artifacts/deps/node/node-sources.txt`
  - `artifacts/deps/node/node-resolve-paths.txt`
- Python：
  - `artifacts/deps/python/python-deps-status.txt`

### J3. 遮蔽/重名模块检查类
- `artifacts/security/shadowing-check.txt`
- `artifacts/security/duplicate-module-names.txt`

### J4. 静态检查类（伪集成/未使用导入）
- `artifacts/static/ununsed-imports.txt`
- `artifacts/static/false-integration-check.txt`

### J5. 测试报告类
- `artifacts/tests/flutter-test-report.txt`
- `artifacts/tests/nest-test-report.txt`
- `artifacts/tests/e2e-ws-report.txt`

### J6. 可观测证据类
- `artifacts/observability/trace-export.json`
- `artifacts/observability/correlation-ids.txt`
- `artifacts/observability/service-logs.txt`
- `artifacts/observability/e2e-timeline.txt`

### J7. 运行环境与复现信息
- `artifacts/runbook/repro-steps.md`
- `artifacts/runbook/versions.txt`

---

## K) MVP 最小链路的固定口径（Always）

### K1. WS 主通道最小消息集合（契约必须固定）
客户端 → 服务端：
- `auth`
- `join_class_session`
- `event`（仅 `class_enter`）

服务端 → 客户端：
- `ack`
- `class_session_aggregate`

### K2. class_session_aggregate 的人数口径（Always）
- 采用 `joined_count`：成功 `auth` 且 `join_class_session` 成功的连接数
- 不允许同时存在 `online_count`（防口径漂移）

### K3. PR-2 最小 E2E 验收阈值（Always）
- `auth` 成功
- `join_class_session` 成功
- 发送 `class_enter` 后：
  - 1 秒内收到 `ack`
  - 1 秒内收到 `class_session_aggregate`
- 单连接场景：
  - `joined_count == 1`
  - `enter_event_count == 1`
- 双连接场景：
  - `joined_count == 2`
  - `enter_event_count == 2`
- 重复 join 幂等：
  - `joined_count` 不得重复增加
- 断开连接：
  - `joined_count` 必须在规定窗口内减少（MVP 允许仅基于断开，不要求心跳）

---

## L) 不得输出代码（本规则文件的使用约束）
- 在规则设计、步骤拆解、CI 与审计规范阶段：严禁输出任何实现代码，只输出清晰、可执行的指令与验收标准。
- 进入实现阶段时仍必须遵守：每步小而具体、每步有测试、每步可观测证据、依赖完整复用、反 monolith。

---