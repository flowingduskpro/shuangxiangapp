import { Global, Module } from '@nestjs/common';

import { loadEnv } from '../../config/app_env';
import { createRedisClient } from './redis.client';

export const REDIS = Symbol('REDIS');

@Global()
@Module({
  providers: [
    {
      provide: REDIS,
      useFactory: () => {
        const env = loadEnv();
        return createRedisClient(env.redisUrl);
      },
    },
  ],
  exports: [REDIS],
})
export class RedisModule {}
