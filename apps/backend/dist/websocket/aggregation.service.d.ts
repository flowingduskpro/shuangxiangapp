import { PrismaService } from '../database/prisma.service';
import { RedisService } from '../database/redis.service';
import { ClassSessionAggregate } from './ws-messages.dto';
export declare class AggregationService {
    private prisma;
    private redis;
    constructor(prisma: PrismaService, redis: RedisService);
    private getJoinedKey;
    private getCountKey;
    addJoinedUser(sessionId: string, userId: string): Promise<number>;
    removeJoinedUser(sessionId: string, userId: string): Promise<number>;
    getJoinedCount(sessionId: string): Promise<number>;
    incrementEnterCount(sessionId: string): Promise<number>;
    getEnterCount(sessionId: string): Promise<number>;
    getAggregate(sessionId: string): Promise<ClassSessionAggregate>;
    recordEvent(sessionId: string, userId: string, eventType: string, correlationId: string, eventData?: Record<string, any>): Promise<void>;
}
