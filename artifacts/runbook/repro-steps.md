# Reproduction Steps - ShuangxiangApp

**Generated:** 2026-02-01 12:21:38 UTC  
**Project:** ShuangxiangApp Backend  
**Purpose:** Complete environment setup and test reproduction guide

---

## Prerequisites

### Required Software
- **Node.js**: v18.x or v20.x (LTS recommended)
- **npm**: v9.x or higher
- **Git**: v2.x
- **Docker** (optional, for Redis/Postgres): v20.x or higher

### System Requirements
- **OS**: Linux, macOS, or Windows with WSL2
- **RAM**: Minimum 4GB, recommended 8GB
- **Disk Space**: 2GB free space

---

## Initial Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-org/shuangxiangapp.git
cd shuangxiangapp
```

### 2. Install Backend Dependencies
```bash
cd apps/backend
npm install
```

### 3. Environment Configuration
Create `.env` file in `apps/backend/`:
```bash
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/shuangxiang"

# JWT
JWT_SECRET="your-secret-key-change-in-production"

# Redis (optional)
REDIS_HOST="localhost"
REDIS_PORT="6379"

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
```

### 4. Database Setup
```bash
# Run Prisma migrations
npx prisma migrate dev

# Generate Prisma client
npx prisma generate
```

### 5. Start Services

#### Option A: Docker Compose (Recommended)
```bash
cd ../../
docker-compose up -d
```

#### Option B: Manual Setup
```bash
# Start PostgreSQL and Redis separately
# Then start backend:
cd apps/backend
npm run start:dev
```

---

## Running Tests

### Unit Tests
```bash
cd apps/backend
npm test
```

### E2E Tests
```bash
cd apps/backend
npm run test:e2e
```

### E2E Test Client
```bash
cd test-client
npm install
node e2e-test.js
```

---

## Reproducing Common Issues

### Issue: WebSocket Connection Fails

**Symptoms:**
- Client cannot connect to ws://localhost:3000
- Connection refused or timeout errors

**Steps to Reproduce:**
1. Start backend: `npm run start:dev`
2. Run test client: `node test-client/e2e-test.js`
3. Observe connection error

**Solution:**
1. Verify backend is running: `curl http://localhost:3000/health`
2. Check firewall settings allow port 3000
3. Ensure WebSocket gateway is enabled in AppModule
4. Check logs: `tail -f apps/backend/logs/*.log`

---

### Issue: Authentication Token Invalid

**Symptoms:**
- 401 Unauthorized errors
- Token verification fails

**Steps to Reproduce:**
1. Generate token with incorrect secret
2. Attempt authenticated request
3. Observe 401 error

**Solution:**
1. Verify JWT_SECRET in .env matches across services
2. Check token expiration (default 1h)
3. Regenerate token: `POST /auth/login`

---

### Issue: Database Connection Fails

**Symptoms:**
- Prisma client errors
- "Cannot connect to database" messages

**Steps to Reproduce:**
1. Stop PostgreSQL service
2. Start backend
3. Observe connection errors

**Solution:**
1. Verify PostgreSQL is running: `docker ps` or `systemctl status postgresql`
2. Check DATABASE_URL format in .env
3. Test connection: `psql $DATABASE_URL`
4. Run migrations: `npx prisma migrate deploy`

---

### Issue: OpenTelemetry Traces Not Appearing

**Symptoms:**
- No traces in OTLP collector
- Silent failure, no errors

**Steps to Reproduce:**
1. Start backend with OTEL configuration
2. Make API requests
3. Check collector, no traces appear

**Solution:**
1. Verify OTEL_EXPORTER_OTLP_ENDPOINT is reachable
2. Check tracing initialization in main.ts
3. Ensure sampling rate is not 0
4. Review collector configuration
5. Test endpoint: `curl http://localhost:4318/v1/traces`

---

## Debugging Guide

### Enable Debug Logging
```bash
export LOG_LEVEL=debug
npm run start:dev
```

### Inspect OpenTelemetry Traces
```bash
# View traces in console (if using ConsoleSpanExporter)
export OTEL_LOG_LEVEL=debug
```

### Database Query Logging
```bash
# Add to .env
DATABASE_LOGGING=true
```

### WebSocket Debug Mode
```typescript
// In main.ts, enable CORS and logging
app.enableCors({ 
  origin: true,
  credentials: true 
});
```

---

## Performance Testing

### Load Test with Artillery
```bash
npm install -g artillery
artillery quick --count 100 --num 10 http://localhost:3000/api/endpoint
```

### WebSocket Load Test
```bash
cd test-client
# Modify e2e-test.js to loop N times
node e2e-test.js
```

---

## Cleanup

### Reset Database
```bash
cd apps/backend
npx prisma migrate reset
```

### Clear Redis Cache
```bash
redis-cli FLUSHALL
```

### Remove Containers
```bash
docker-compose down -v
```

---

## CI/CD Reproduction

### Generate All Artifacts
```bash
./scripts/generate-artifacts.sh
```

### Verify Artifact Generation
```bash
ls -R artifacts/
```

### Check Artifact Validation
```bash
cat artifacts/audit/report-validation-result.json
```

---

## Troubleshooting Checklist

- [ ] Node.js version correct (`node --version`)
- [ ] All dependencies installed (`npm ls` shows no errors)
- [ ] .env file configured with valid values
- [ ] Database is running and accessible
- [ ] Redis is running (if using)
- [ ] Port 3000 is available (`lsof -i :3000`)
- [ ] Firewall allows inbound connections
- [ ] OpenTelemetry collector is reachable
- [ ] Logs directory exists and is writable

---

## Support

For additional help:
- Check logs in `apps/backend/logs/`
- Review GitHub Issues
- Consult API documentation in `docs/`

**Last Updated:** 2026-02-01 12:21:38 UTC
