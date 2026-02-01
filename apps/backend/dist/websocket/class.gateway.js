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
var __param = (this && this.__param) || function (paramIndex, decorator) {
    return function (target, key) { decorator(target, key, paramIndex); }
};
var ClassGateway_1;
Object.defineProperty(exports, "__esModule", { value: true });
exports.ClassGateway = void 0;
const websockets_1 = require("@nestjs/websockets");
const socket_io_1 = require("socket.io");
const common_1 = require("@nestjs/common");
const jwt_1 = require("@nestjs/jwt");
const config_1 = require("@nestjs/config");
const aggregation_service_1 = require("./aggregation.service");
const session_service_1 = require("../session/session.service");
const ws_messages_dto_1 = require("./ws-messages.dto");
const uuid_1 = require("uuid");
const ws_exception_filter_1 = require("./ws-exception.filter");
let ClassGateway = ClassGateway_1 = class ClassGateway {
    constructor(jwtService, configService, aggregationService, sessionService) {
        this.jwtService = jwtService;
        this.configService = configService;
        this.aggregationService = aggregationService;
        this.sessionService = sessionService;
        this.logger = new common_1.Logger(ClassGateway_1.name);
        this.sessions = new Map();
    }
    handleConnection(client) {
        this.logger.log(`Client connected: ${client.id}`);
        this.sessions.set(client.id, {
            userId: null,
            classSessionId: null,
            authenticated: false,
            jwtPayload: null,
        });
    }
    async handleDisconnect(client) {
        this.logger.log(`Client disconnected: ${client.id}`);
        const session = this.sessions.get(client.id);
        if (session?.classSessionId && session?.userId) {
            const count = await this.aggregationService.removeJoinedUser(session.classSessionId, session.userId);
            const aggregate = await this.aggregationService.getAggregate(session.classSessionId);
            this.server.to(session.classSessionId).emit('class_session_aggregate', aggregate);
        }
        this.sessions.delete(client.id);
    }
    async handleAuth(client, data) {
        const correlationId = (0, uuid_1.v4)();
        try {
            const payload = this.jwtService.verify(data.token, {
                secret: this.configService.get('jwt.secret'),
                issuer: this.configService.get('jwt.issuer'),
            });
            const session = this.sessions.get(client.id);
            session.userId = payload.sub;
            session.authenticated = true;
            session.jwtPayload = payload;
            this.sessions.set(client.id, session);
            this.logger.log(`Client ${client.id} authenticated as user ${payload.sub}`);
            return {
                correlation_id: correlationId,
                timestamp: new Date().toISOString(),
                status: 'success',
            };
        }
        catch (error) {
            this.logger.error(`Auth failed for client ${client.id}: ${error.message}`);
            return {
                correlation_id: correlationId,
                timestamp: new Date().toISOString(),
                status: 'error',
                message: 'Authentication failed',
            };
        }
    }
    async handleJoinClassSession(client, data) {
        const correlationId = (0, uuid_1.v4)();
        const session = this.sessions.get(client.id);
        if (!session?.authenticated) {
            return {
                correlation_id: correlationId,
                timestamp: new Date().toISOString(),
                status: 'error',
                message: 'Not authenticated',
            };
        }
        try {
            const classSession = await this.sessionService.getSession(data.class_session_id);
            if (!classSession) {
                return {
                    correlation_id: correlationId,
                    timestamp: new Date().toISOString(),
                    status: 'error',
                    message: 'Class session not found',
                };
            }
            session.classSessionId = data.class_session_id;
            this.sessions.set(client.id, session);
            client.join(data.class_session_id);
            await this.aggregationService.addJoinedUser(data.class_session_id, session.userId);
            const aggregate = await this.aggregationService.getAggregate(data.class_session_id);
            this.server.to(data.class_session_id).emit('class_session_aggregate', aggregate);
            this.logger.log(`Client ${client.id} joined session ${data.class_session_id}`);
            return {
                correlation_id: correlationId,
                timestamp: new Date().toISOString(),
                status: 'success',
            };
        }
        catch (error) {
            this.logger.error(`Join failed: ${error.message}`);
            return {
                correlation_id: correlationId,
                timestamp: new Date().toISOString(),
                status: 'error',
                message: 'Failed to join session',
            };
        }
    }
    async handleEvent(client, data) {
        const correlationId = (0, uuid_1.v4)();
        const session = this.sessions.get(client.id);
        if (!session?.authenticated || !session?.classSessionId) {
            return {
                correlation_id: correlationId,
                timestamp: new Date().toISOString(),
                status: 'error',
                message: 'Not authenticated or not in session',
            };
        }
        if (data.event_type !== 'class_enter') {
            return {
                correlation_id: correlationId,
                timestamp: new Date().toISOString(),
                status: 'error',
                message: 'Unsupported event type',
            };
        }
        try {
            await this.aggregationService.recordEvent(session.classSessionId, session.userId, data.event_type, correlationId, data.event_data);
            await this.aggregationService.incrementEnterCount(session.classSessionId);
            const aggregate = await this.aggregationService.getAggregate(session.classSessionId);
            this.server.to(session.classSessionId).emit('class_session_aggregate', aggregate);
            this.logger.log(`Event ${data.event_type} recorded for session ${session.classSessionId}`);
            return {
                correlation_id: correlationId,
                timestamp: new Date().toISOString(),
                status: 'success',
            };
        }
        catch (error) {
            this.logger.error(`Event recording failed: ${error.message}`);
            return {
                correlation_id: correlationId,
                timestamp: new Date().toISOString(),
                status: 'error',
                message: 'Failed to record event',
            };
        }
    }
};
exports.ClassGateway = ClassGateway;
__decorate([
    (0, websockets_1.WebSocketServer)(),
    __metadata("design:type", socket_io_1.Server)
], ClassGateway.prototype, "server", void 0);
__decorate([
    (0, websockets_1.SubscribeMessage)('auth'),
    __param(0, (0, websockets_1.ConnectedSocket)()),
    __param(1, (0, websockets_1.MessageBody)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [socket_io_1.Socket,
        ws_messages_dto_1.AuthMessageDto]),
    __metadata("design:returntype", Promise)
], ClassGateway.prototype, "handleAuth", null);
__decorate([
    (0, websockets_1.SubscribeMessage)('join_class_session'),
    __param(0, (0, websockets_1.ConnectedSocket)()),
    __param(1, (0, websockets_1.MessageBody)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [socket_io_1.Socket,
        ws_messages_dto_1.JoinClassSessionDto]),
    __metadata("design:returntype", Promise)
], ClassGateway.prototype, "handleJoinClassSession", null);
__decorate([
    (0, websockets_1.SubscribeMessage)('event'),
    __param(0, (0, websockets_1.ConnectedSocket)()),
    __param(1, (0, websockets_1.MessageBody)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [socket_io_1.Socket,
        ws_messages_dto_1.EventMessageDto]),
    __metadata("design:returntype", Promise)
], ClassGateway.prototype, "handleEvent", null);
exports.ClassGateway = ClassGateway = ClassGateway_1 = __decorate([
    (0, websockets_1.WebSocketGateway)({
        cors: {
            origin: '*',
            credentials: true,
        },
    }),
    (0, common_1.UseFilters)(ws_exception_filter_1.WsExceptionFilter),
    __metadata("design:paramtypes", [jwt_1.JwtService,
        config_1.ConfigService,
        aggregation_service_1.AggregationService,
        session_service_1.SessionService])
], ClassGateway);
//# sourceMappingURL=class.gateway.js.map