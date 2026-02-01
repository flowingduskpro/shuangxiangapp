# MVP Runbook: 基础框架可跑通（WS 主通道）

## 概述

本文档说明如何在干净环境中运行和验证 WS 主通道的最小闭环链路：

```
WS connect → auth(JWT) → join_class_session → event(class_enter) 
→ PostgreSQL write (Prisma) → Redis aggregate update 
→ WS push(class_session_aggregate)
```

## 前置依赖

- Docker 与 Docker Compose v2
- Node.js v20+
- curl (用于 REST API 测试)

## 快速启动

### 1. 启动基础设施（PostgreSQL + Redis + Backend）

```bash
# 在项目根目录
docker compose up -d postgres redis

# 等待服务就绪（约 10 秒）
docker compose ps

# 运行数据库迁移
cd apps/backend
npm install
npx prisma migrate deploy

# 启动后端服务
npm run start:dev
```

后端将在 `http://localhost:3000` 启动。

### 2. 创建 Class Session

使用 REST API 创建一个测试用的 class_session：

```bash
# 生成测试 JWT token（使用 Node.js）
node -e "
const jwt = require('jsonwebtoken');
const token = jwt.sign(
  { sub: 'user-1', role: 'student', class_id: 'class-1' },
  'dev-secret-change-in-production',
  { issuer: 'shuangxiang-app', expiresIn: '1h' }
);
console.log(token);
" > /tmp/token.txt

TOKEN=$(cat /tmp/token.txt)

# 创建 class session
curl -X POST http://localhost:3000/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"class_id": "class-1"}' \
  | tee /tmp/session.json

# 提取 class_session_id
CLASS_SESSION_ID=$(cat /tmp/session.json | grep -o '"class_session_id":"[^"]*"' | cut -d'"' -f4)
echo "Class Session ID: $CLASS_SESSION_ID"
```

### 3. 运行 E2E 测试

```bash
cd ../test-client

# 运行 E2E 测试脚本
CLASS_SESSION_ID=$CLASS_SESSION_ID \
SERVER_URL=http://localhost:3000 \
JWT_SECRET=dev-secret-change-in-production \
node e2e-test.js
```

**期望输出**：

```
[AUTH] SUCCESS - Time: <15ms
[JOIN] SUCCESS - Time: <20ms
[EVENT] SUCCESS - Time: <45ms
[ACK] Received in <1000ms
[AGGREGATE] Received in <1000ms
Overall: ✓ PASS
```

## 验收阈值验证

### 单连接场景

- ✅ 发送 `class_enter` 后 1 秒内收到 `ack`
- ✅ 发送 `class_enter` 后 1 秒内收到 `class_session_aggregate`
- ✅ `joined_count == 1`
- ✅ `enter_event_count == 1`

### 双连接场景

```bash
# 在两个终端中分别运行
CLASS_SESSION_ID=$CLASS_SESSION_ID node e2e-test.js
```

观察最终的 aggregate：`joined_count == 2`, `enter_event_count == 2`

## 运行集成测试

```bash
cd apps/backend
npm run test:e2e
```

## 可观测性验证

### Correlation ID 追踪

从 E2E 测试输出中获取 correlation ID，在 PostgreSQL 和服务端日志中追踪。

## 向后兼容策略

当前为 MVP v1.0。未来版本更新时：
- WebSocket 消息必须包含 `version` 字段
- 服务端必须支持至少前 1 个主版本的消息格式
- 数据库 migration 必须是可回滚的（通过 Prisma migrate）

## 回滚方式

如果部署失败：

1. 停止新版本服务
2. 回滚数据库迁移：
   ```bash
   npx prisma migrate resolve --rolled-back <migration_name>
   ```
3. 启动旧版本服务

## 清理环境

```bash
docker compose down -v
```

