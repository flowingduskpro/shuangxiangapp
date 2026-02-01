jishuzhan

## （默认推荐）：Flutter 全端 + TypeScript 后端 + Python AI 服务

### 1) 客户端

- **教师端 App**：Flutter（iOS/Android）
- **学生端 App**：Flutter（iOS/Android）
- 关键依赖：
  - 状态管理：Riverpod（或 Bloc）
  - 网络：Dio
  - 本地存储：Hive / Drift(SQLite)
  - 埋点：自建埋点 SDK（或用 OpenTelemetry/自定义协议）+ 崩溃：Sentry

为什么推荐 Flutter：两端都做 App 时，Flutter 能把交互、课堂态势页、投票小测组件、报告页统一复用；同时对“前后台、页面栈、生命周期”埋点也好做。

### 2) 后端（业务与实时）

- **API 层 / BFF**：NestJS（TypeScript）
- **实时**：WebSocket（NestJS Gateway）用于课堂态势、投票、小测、实时反馈
- **异步任务**：BullMQ（Redis）用于报告生成、推荐计算、OCR/解析任务编排

### 3) 数据与事件

- **主库**：PostgreSQL（课程、章节、知识点、反馈、评分规则、任务）

- **缓存/聚合**：Redis（课堂中实时聚合：人数、退出/切屏/无操作计数、热点知识点）

- 行为事件明细

  ：

  - MVP：PostgreSQL 分区表（按天/按 class_session_id）
  - V1：上 ClickHouse（更适合高频事件与报表查询）

### 4) AI/内容处理（独立服务，避免拖慢业务迭代）

- Python FastAPI

  ：

  - OCR：PaddleOCR（中文强）/ Tesseract（备选）
  - 文本解析与知识点抽取：LLM 调用 + 规则后处理
  - 推荐计算：规则打分（MVP）→ embedding（V1）

- 向量检索（V1可选）：

  - pgvector（简单够用）或 Milvus（规模更大）

### 5) 存储与基础设施

- 对象存储：S3 兼容（MinIO / 阿里 OSS / 腾讯 COS）
- 可观测：OpenTelemetry + Prometheus + Grafana；日志 Loki；错误 Sentry
- 部署：Docker（MVP）→ Kubernetes（V1）