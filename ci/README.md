# CI 配置目录（ci/）

本目录用于存放 CI 门禁所需的可审计配置。

- `line-limit-whitelist.json`：单文件行数超过阈值时的白名单（必须填写原因与到期日）。
- `mvp-scope-rules.yml`：MVP Scope Gate 的关键字黑名单规则（命中即 hard fail）。

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

## Gate 4 (Dependency Integrity) - 本地运行

Gate 4 会生成《依赖完整性审计报告》：
- `ci_artifacts/dependency-audit.md`（必有）

说明：当前仓库可能尚未落地 apps/services 真实代码与依赖清单；在“无依赖清单文件”的阶段，Gate 4 会输出 N/A 并通过，但仍会生成可追溯的审计报告。

### 运行方式（本地）

```powershell
python ci/scripts/dependency_gate.py
```

### 失败条件（对应该 Gate 4）

- 发现依赖清单（例如 `pubspec.yaml` / `package.json` / `requirements.txt` / `pyproject.toml`），但缺少对应的锁定/可复现机制（例如 `pubspec.lock` / Node lockfile / Python lockfile 或严格 pin）。

> 更完整的约束与证据格式，以 `memory_bank/implementation-plan.md` 第 4 节为准。

## Gate 5 (Tests) - 本地运行

Gate 5 对应 `memory_bank/implementation-plan.md` 第 5 节（Tests Gate：每一步必须有测试）。

当前仓库仍可能处于“仅文档/目录尚未落代码”的阶段，因此脚本采取与 Gate 4 类似的策略：
- 如果仓库里没有任何 Flutter/Node/Python 的依赖清单（manifest），则该技术栈结论为 N/A，门禁整体 PASS；
- 一旦出现对应 manifest，则开始要求最小测试骨架存在（例如 `tests/`、`integration_test/` 或 `test` 配置）。

### 运行方式（本地）

```powershell
python ci/scripts/tests_gate.py
```

### 输出产物

脚本会生成：
- `ci_artifacts/tests-report.json`（必有）

### 失败条件（对应该 Gate 5 的最小可机器检查子集）

- Flutter：存在 `pubspec.yaml` 但同目录缺少 `integration_test/` 或 `test/`
- Node：存在 `package.json` 但同目录缺少 `test/` 或 `__tests__/`，且 `package.json` 中也没有 `scripts.test` / `jest` 配置
- Python：存在 `requirements.txt` 或 `pyproject.toml` 但同目录缺少 `tests/`

## Gate 6 (Observability) - 本地运行

Gate 6 对应 `memory_bank/implementation-plan.md` 第 6 节（Observability Gate：最小可观测证据）。

当前仓库仍可能处于“仅文档/代码尚未落地”的阶段，因此脚本采取与 Gate 4/5 类似的策略：
- 如果仓库中不存在任何 manifest（`pubspec.yaml` / `package.json` / `requirements.txt` / `pyproject.toml`），结论为 N/A 且整体 PASS；
- 一旦出现 manifest（意味着代码开始落地），就会开始要求 `ci_artifacts/trace-evidence.md` 中包含最小可关联字段（correlation + 业务关键字段）。

### 运行方式（本地）

```powershell
python ci/scripts/observability_gate.py
```

### 输出产物

脚本会生成：
- `ci_artifacts/trace-evidence.md`（必有）

### 失败条件（对应 Gate 6 的最小可机器检查子集）

- 仓库出现 manifest，但缺少 `ci_artifacts/trace-evidence.md`；
- 或 `ci_artifacts/trace-evidence.md` 不包含如下最小关键字：
  - `x-correlation-id`
  - `correlation_id`
  - `class_session_id`（或后续扩展的等价业务关键字段）
