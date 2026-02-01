# CI 配置目录（ci/）

本目录用于存放 CI 门禁所需的可审计配置。

- `line-limit-whitelist.json`：单文件行数超过阈值时的白名单（必须填写原因与到期日）。
- `mvp-scope-rules.yml`：MVP Scope Gate 的关键词黑名单规则（命中即 hard fail）。

> 具体规则见 `memory_bank/implementation-plan.md`。

# ci/

## Gate 2 (Preflight) - 本地运行

本仓库已落地 `memory_bank/implementation-plan.md` 的 Gate 2（Preflight）最小自动化。

### 运行方式（本地）

- 方式 A：直接用环境变量提供 PR Body（适合本地快速验证）

```powershell
$env:PR_BODY = @"
我已阅读 memory_bank/architecture.md
我已阅读 memory_bank/双向个性化课堂管理AI App 产品需求与方案生成器 v1.0.0.md
业务域：课堂/反馈
是否涉及：DB 否；事件契约 否；权限 否；保留/合规 否
"@
python ci/scripts/preflight.py
```

- 方式 B：用文件提供 PR Body（适合较长文本）

```powershell
$env:PR_BODY_FILE = "C:\path\to\pr_body.txt"
python ci/scripts/preflight.py
```

### 输出产物

脚本会生成：
- `ci_artifacts/trace-evidence.md`（必有）
- `ci_artifacts/preflight-report.json`（必有）

### 失败条件（对应 Gate 2）

- Gate 2.1：PR 缺少必读确认记录（阅读声明/业务域/是否涉及关键变更）
- Gate 2.2：当变更命中 `**/migrations/**`、`**/openapi*.{yml,yaml,json}`、`**/jobs/**` 时，必须同时修改 `memory_bank/architecture.md`

> 注意：Structure Gate（行数/目录文件数/import 边界）属于后续步骤，本阶段不执行。

## Gate 3 (Structure) - 本地运行

Gate 3 会检查：
- 业务源代码单文件行数阈值（>250 行即失败；可在 `ci/line-limit-whitelist.json` 登记豁免）
- 单目录同一层级业务源文件数阈值（Flutter/NestJS >25、FastAPI >20）
- import 边界约束（本仓库尚未配置边界规则时为预留字段）

### 运行方式（本地）

```powershell
python ci/scripts/structure_gate.py
```

### 输出产物

脚本会生成：
- `ci_artifacts/structure-report.json`（必有）
