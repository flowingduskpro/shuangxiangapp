import { Injectable } from '@nestjs/common';
import { PrismaService } from '../database/prisma.service';
import { RedisService } from '../database/redis.service';
import { ClassSessionAggregate } from './ws-messages.dto';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class AggregationService {
  constructor(
    private prisma: PrismaService,
    private redis: RedisService,
  ) {}

  private getJoinedKey(sessionId: string): string {
    return `session:${sessionId}:joined`;
  }

  private getCountKey(sessionId: string): string {
    return `session:${sessionId}:enter_count`;
  }

  async addJoinedUser(sessionId: string, userId: string): Promise<number> {
    const key = this.getJoinedKey(sessionId);
    await this.redis.sadd(key, userId);
    return this.redis.scard(key);
  }

  async removeJoinedUser(sessionId: string, userId: string): Promise<number> {
    const key = this.getJoinedKey(sessionId);
    await this.redis.srem(key, userId);
    return this.redis.scard(key);
  }

  async getJoinedCount(sessionId: string): Promise<number> {
    const key = this.getJoinedKey(sessionId);
    return this.redis.scard(key);
  }

  async incrementEnterCount(sessionId: string): Promise<number> {
    const key = this.getCountKey(sessionId);
    return this.redis.incr(key);
  }

  async getEnterCount(sessionId: string): Promise<number> {
    const key = this.getCountKey(sessionId);
    const count = await this.redis.get(key);
    return count ? parseInt(count, 10) : 0;
  }

  async getAggregate(sessionId: string): Promise<ClassSessionAggregate> {
    const joinedCount = await this.getJoinedCount(sessionId);
    const enterEventCount = await this.getEnterCount(sessionId);

    return {
      class_session_id: sessionId,
      joined_count: joinedCount,
      enter_event_count: enterEventCount,
      server_timestamp: new Date().toISOString(),
      version: 'v1',
    };
  }

  async recordEvent(
    sessionId: string,
    userId: string,
    eventType: string,
    correlationId: string,
    eventData?: Record<string, any>,
  ): Promise<void> {
    await this.prisma.classEvent.create({
      data: {
        classSessionId: sessionId,
        userId,
        eventType,
        correlationId,
        eventData: eventData || {},
      },
    });
  }
}
