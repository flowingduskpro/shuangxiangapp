import { Inject, Injectable } from '@nestjs/common';

import type { RedisClient } from '../../infra/redis/redis.client';
import { REDIS } from '../../infra/redis/redis.module';

export type Aggregate = {
  class_session_id: string;
  joined_count: number;
  enter_event_count: number;
  server_timestamp: string;
  version: string;
};

@Injectable()
export class AggregateService {
  constructor(@Inject(REDIS) private readonly redis: RedisClient) {}

  private keyJoined(sessionId: string) {
    return `class_session:${sessionId}:joined_count`;
  }

  private keyEnter(sessionId: string) {
    return `class_session:${sessionId}:enter_event_count`;
  }

  async incEnter(sessionId: string): Promise<number> {
    return await this.redis.incr(this.keyEnter(sessionId));
  }

  async addJoined(sessionId: string): Promise<number> {
    return await this.redis.incr(this.keyJoined(sessionId));
  }

  async removeJoined(sessionId: string): Promise<number> {
    // Decrement but never below 0.
    const key = this.keyJoined(sessionId);
    const val = await this.redis.decr(key);
    if (val < 0) {
      await this.redis.set(key, '0');
      return 0;
    }
    return val;
  }

  async get(sessionId: string, version: string): Promise<Aggregate> {
    const [joinedRaw, enterRaw] = await this.redis.mget(this.keyJoined(sessionId), this.keyEnter(sessionId));
    const joined = Number(joinedRaw ?? '0');
    const enter = Number(enterRaw ?? '0');
    return {
      class_session_id: sessionId,
      joined_count: joined,
      enter_event_count: enter,
      server_timestamp: new Date().toISOString(),
      version,
    };
  }
}
