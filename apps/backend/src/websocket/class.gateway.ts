import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayConnection,
  OnGatewayDisconnect,
  ConnectedSocket,
  MessageBody,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { Logger, UseFilters } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import { AggregationService } from './aggregation.service';
import { SessionService } from '../session/session.service';
import {
  AuthMessageDto,
  JoinClassSessionDto,
  EventMessageDto,
  AckResponse,
} from './ws-messages.dto';
import { v4 as uuidv4 } from 'uuid';
import { WsExceptionFilter } from './ws-exception.filter';
import { JwtPayload } from '../auth/jwt-payload.interface';

interface ClientSession {
  userId: string;
  classSessionId: string | null;
  authenticated: boolean;
  jwtPayload: JwtPayload | null;
}

@WebSocketGateway({
  cors: {
    origin: '*',
    credentials: true,
  },
})
@UseFilters(WsExceptionFilter)
export class ClassGateway implements OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server: Server;

  private readonly logger = new Logger(ClassGateway.name);
  private readonly sessions = new Map<string, ClientSession>();

  constructor(
    private jwtService: JwtService,
    private configService: ConfigService,
    private aggregationService: AggregationService,
    private sessionService: SessionService,
  ) {}

  handleConnection(client: Socket) {
    this.logger.log(`Client connected: ${client.id}`);
    this.sessions.set(client.id, {
      userId: null,
      classSessionId: null,
      authenticated: false,
      jwtPayload: null,
    });
  }

  async handleDisconnect(client: Socket) {
    this.logger.log(`Client disconnected: ${client.id}`);
    const session = this.sessions.get(client.id);
    
    if (session?.classSessionId && session?.userId) {
      const count = await this.aggregationService.removeJoinedUser(
        session.classSessionId,
        session.userId,
      );
      
      const aggregate = await this.aggregationService.getAggregate(
        session.classSessionId,
      );
      this.server.to(session.classSessionId).emit('class_session_aggregate', aggregate);
    }
    
    this.sessions.delete(client.id);
  }

  @SubscribeMessage('auth')
  async handleAuth(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: AuthMessageDto,
  ): Promise<AckResponse> {
    const correlationId = uuidv4();
    
    try {
      const payload = this.jwtService.verify<JwtPayload>(data.token, {
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
    } catch (error) {
      this.logger.error(`Auth failed for client ${client.id}: ${error.message}`);
      return {
        correlation_id: correlationId,
        timestamp: new Date().toISOString(),
        status: 'error',
        message: 'Authentication failed',
      };
    }
  }

  @SubscribeMessage('join_class_session')
  async handleJoinClassSession(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: JoinClassSessionDto,
  ): Promise<AckResponse> {
    const correlationId = uuidv4();
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
      const classSession = await this.sessionService.getSession(
        data.class_session_id,
      );

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

      await this.aggregationService.addJoinedUser(
        data.class_session_id,
        session.userId,
      );

      const aggregate = await this.aggregationService.getAggregate(
        data.class_session_id,
      );

      this.server.to(data.class_session_id).emit('class_session_aggregate', aggregate);

      this.logger.log(
        `Client ${client.id} joined session ${data.class_session_id}`,
      );

      return {
        correlation_id: correlationId,
        timestamp: new Date().toISOString(),
        status: 'success',
      };
    } catch (error) {
      this.logger.error(`Join failed: ${error.message}`);
      return {
        correlation_id: correlationId,
        timestamp: new Date().toISOString(),
        status: 'error',
        message: 'Failed to join session',
      };
    }
  }

  @SubscribeMessage('event')
  async handleEvent(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: EventMessageDto,
  ): Promise<AckResponse> {
    const correlationId = uuidv4();
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
      await this.aggregationService.recordEvent(
        session.classSessionId,
        session.userId,
        data.event_type,
        correlationId,
        data.event_data,
      );

      await this.aggregationService.incrementEnterCount(session.classSessionId);

      const aggregate = await this.aggregationService.getAggregate(
        session.classSessionId,
      );

      this.server.to(session.classSessionId).emit('class_session_aggregate', aggregate);

      this.logger.log(
        `Event ${data.event_type} recorded for session ${session.classSessionId}`,
      );

      return {
        correlation_id: correlationId,
        timestamp: new Date().toISOString(),
        status: 'success',
      };
    } catch (error) {
      this.logger.error(`Event recording failed: ${error.message}`);
      return {
        correlation_id: correlationId,
        timestamp: new Date().toISOString(),
        status: 'error',
        message: 'Failed to record event',
      };
    }
  }
}
