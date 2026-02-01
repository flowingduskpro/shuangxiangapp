# CI 配置目录（ci/）

本目录用于存放 CI 门禁所需的可审计配置。

- `line-limit-whitelist.json`：单文件行数超过阈值时的白名单（必须填写原因与到期日）。
- `mvp-scope-rules.yml`：MVP Scope Gate 的关键词黑名单规则（命中即 hard fail）。

> 具体规则见 `memory_bank/implementation-plan.md`。
