import 'reflect-metadata';

import { NestFactory } from '@nestjs/core';

import { AppModule } from './modules/app.module';
import { startOtel, stopOtel } from './infra/observability/otel';

async function bootstrap() {
  await startOtel();

  const app = await NestFactory.create(AppModule, { logger: ['log', 'error', 'warn'] });
  const port = Number(process.env.PORT ?? '3000');

  // Gate 6 requires correlation tokens to be visible in service logs.
  // We log them *only if present* on inbound HTTP requests.
  app.use((req: any, _res: any, next: any) => {
    try {
      const h = req?.headers ?? {};
      const xcid = h['x-correlation-id'] ?? h['X-Correlation-Id'];
      const cid = h['correlation_id'] ?? h['correlation-id'];
      const csid = h['class_session_id'] ?? h['class-session-id'];
      if (xcid) {
        console.log(`x-correlation-id ${xcid}`);
      }
      if (cid) {
        console.log(`correlation_id ${cid}`);
      }
      if (csid) {
        console.log(`class_session_id ${csid}`);
      }
    } catch {
      // ignore
    }
    next();
  });

  const shutdown = async () => {
    try {
      await app.close();
    } finally {
      await stopOtel();
    }
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  await app.listen(port);
}

bootstrap();
