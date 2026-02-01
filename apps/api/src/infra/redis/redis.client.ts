import Redis from 'ioredis';

export type RedisClient = InstanceType<typeof Redis>;

export function createRedisClient(redisUrl: string): RedisClient {
  return new Redis(redisUrl);
}

// Optional logging hooks for inbound HTTP requests
export function logCorrelationId(correlationId?: string) {
  if (correlationId) {
    console.log(`x-correlation-id: ${correlationId}`);
  }
}

export function logClassSessionId(classSessionId?: string) {
  if (classSessionId) {
    console.log(`class_session_id: ${classSessionId}`);
  }
}
