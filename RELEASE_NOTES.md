# Release Notes

## v1.0.0 - MVP: 基础框架可跑通（WS 主通道）

**发布日期**: 2024-02-01

### Impact / 影响范围

- **新增**: 完整的 WebSocket 主通道实现
- **新增**: NestJS 后端服务 (apps/backend)
- **新增**: PostgreSQL 数据库 schema (class_sessions, class_events)
- **新增**: Redis 聚合服务
- **新增**: Docker Compose 基础设施
- **影响对象**: 所有客户端（当前为 test-client，未来包括 Flutter app）

### 功能清单

#### WebSocket 主通道
- ✅ WS 认证 (JWT)
- ✅ join_class_session
- ✅ event (class_enter)
- ✅ 实时聚合推送 (class_session_aggregate)

#### 数据层
- ✅ Prisma ORM + PostgreSQL
- ✅ Redis 缓存与聚合
- ✅ 事件明细按 class_session_id 可查询

#### 测试与验证
- ✅ 集成测试套件
- ✅ E2E 测试客户端
- ✅ 1秒内 ack/aggregate 验证

### Rollback / 回滚方式

如需回滚：

1. **停止服务**:
   ```bash
   docker compose down
   ```

2. **回滚数据库迁移**:
   ```bash
   cd apps/backend
   npx prisma migrate resolve --rolled-back 20240201000000_init
   ```

3. **恢复数据** (如有备份):
   ```bash
   docker compose exec postgres psql -U postgres -d shuangxiang < backup.sql
   ```

4. **启动旧版本**:
   ```bash
   git checkout <previous-commit>
   docker compose up -d
   ```

### 注意事项

- 首次发布，无向后兼容问题
- 数据库迁移可安全回滚（DROP TABLE）
- Redis 数据为临时缓存，清空无影响

### 相关文档

- 架构文档: `memory_bank/architecture.md`
- 运行手册: `docs/runbook/mvp.md`
- 实施计划: `memory_bank/implementation-plan.md`

