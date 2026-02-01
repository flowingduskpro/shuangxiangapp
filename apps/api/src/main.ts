import 'reflect-metadata';

import { NestFactory } from '@nestjs/core';

import { AppModule } from './modules/app.module';
import { startOtel, stopOtel } from './infra/observability/otel';

async function bootstrap() {
  await startOtel();

  const app = await NestFactory.create(AppModule, { logger: ['log', 'error', 'warn'] });
  const port = Number(process.env.PORT ?? '3000');

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
