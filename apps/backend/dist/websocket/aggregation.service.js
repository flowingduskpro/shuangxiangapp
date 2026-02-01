"use strict";
var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.AggregationService = void 0;
const common_1 = require("@nestjs/common");
const prisma_service_1 = require("../database/prisma.service");
const redis_service_1 = require("../database/redis.service");
let AggregationService = class AggregationService {
    constructor(prisma, redis) {
        this.prisma = prisma;
        this.redis = redis;
    }
    getJoinedKey(sessionId) {
        return `session:${sessionId}:joined`;
    }
    getCountKey(sessionId) {
        return `session:${sessionId}:enter_count`;
    }
    async addJoinedUser(sessionId, userId) {
        const key = this.getJoinedKey(sessionId);
        await this.redis.sadd(key, userId);
        return this.redis.scard(key);
    }
    async removeJoinedUser(sessionId, userId) {
        const key = this.getJoinedKey(sessionId);
        await this.redis.srem(key, userId);
        return this.redis.scard(key);
    }
    async getJoinedCount(sessionId) {
        const key = this.getJoinedKey(sessionId);
        return this.redis.scard(key);
    }
    async incrementEnterCount(sessionId) {
        const key = this.getCountKey(sessionId);
        return this.redis.incr(key);
    }
    async getEnterCount(sessionId) {
        const key = this.getCountKey(sessionId);
        const count = await this.redis.get(key);
        return count ? parseInt(count, 10) : 0;
    }
    async getAggregate(sessionId) {
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
    async recordEvent(sessionId, userId, eventType, correlationId, eventData) {
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
};
exports.AggregationService = AggregationService;
exports.AggregationService = AggregationService = __decorate([
    (0, common_1.Injectable)(),
    __metadata("design:paramtypes", [prisma_service_1.PrismaService,
        redis_service_1.RedisService])
], AggregationService);
//# sourceMappingURL=aggregation.service.js.map