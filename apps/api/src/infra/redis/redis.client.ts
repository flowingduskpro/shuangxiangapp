import Redis from 'ioredis';

export type RedisClient = InstanceType<typeof Redis>;

export function createRedisClient(redisUrl: string): RedisClient {
  return new Redis(redisUrl);
}
