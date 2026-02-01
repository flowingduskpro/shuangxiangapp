import { OnGatewayConnection, OnGatewayDisconnect } from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import { AggregationService } from './aggregation.service';
import { SessionService } from '../session/session.service';
import { AuthMessageDto, JoinClassSessionDto, EventMessageDto, AckResponse } from './ws-messages.dto';
export declare class ClassGateway implements OnGatewayConnection, OnGatewayDisconnect {
    private jwtService;
    private configService;
    private aggregationService;
    private sessionService;
    server: Server;
    private readonly logger;
    private readonly sessions;
    constructor(jwtService: JwtService, configService: ConfigService, aggregationService: AggregationService, sessionService: SessionService);
    handleConnection(client: Socket): void;
    handleDisconnect(client: Socket): Promise<void>;
    handleAuth(client: Socket, data: AuthMessageDto): Promise<AckResponse>;
    handleJoinClassSession(client: Socket, data: JoinClassSessionDto): Promise<AckResponse>;
    handleEvent(client: Socket, data: EventMessageDto): Promise<AckResponse>;
}
