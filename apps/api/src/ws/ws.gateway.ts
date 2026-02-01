import { Logger } from '@nestjs/common';
import {
  ConnectedSocket,
  MessageBody,
  OnGatewayDisconnect,
  SubscribeMessage,
  WebSocketGateway,
} from '@nestjs/websockets';
import type { Socket } from 'socket.io';
import { v4 as uuidv4 } from 'uuid';

import { AggregateService } from '../domain/aggregate/aggregate.service';
import { JwtAuthService } from '../domain/auth/jwt_auth.service';
import { ClassEventService } from '../domain/events/class_event.service';
import type { WsClientToServer, WsServerAck, WsServerAggregate } from './ws.types';
import { getTracer } from '../infra/observability/otel';

type SocketWithSession = Socket & { data: { session?: any } };

@WebSocketGateway({
  cors: { origin: '*' },
})
export class WsGateway implements OnGatewayDisconnect {
  private readonly log = new Logger(WsGateway.name);

  constructor(
    private readonly auth: JwtAuthService,
    private readonly events: ClassEventService,
    private readonly aggregates: AggregateService,
  ) {}

  private getVersion(msg: { version?: string } | undefined): string {
    return msg?.version ?? 'pr-2.0.0';
  }

  private ack(version: string, correlationId: string, ackType: string, ok: boolean, error?: string | null): WsServerAck {
    return {
      msg_type: 'ack',
      version,
      correlation_id: correlationId,
      ok,
      ack_type: ackType,
      error: error ?? null,
    };
  }

  async handleDisconnect(client: SocketWithSession) {
    const tracer = getTracer();
    return await tracer.startActiveSpan('ws.disconnect', async (span) => {
      try {
        const session = client.data.session;
        const sessionId = session?.classSessionId as string | undefined;
        const correlationId = session?.correlationId ?? 'disconnect';

        span.setAttribute('correlation_id', correlationId);
        if (sessionId) span.setAttribute('class_session_id', sessionId);

        if (session?.joined && sessionId) {
          const joined = await this.aggregates.removeJoined(sessionId);
          span.setAttribute('joined_count', joined);
          this.log.log(
            `disconnect correlation_id=${correlationId} class_session_id=${sessionId} joined_count=${joined}`,
          );
        }
      } catch (e: any) {
        span.recordException(e);
        this.log.error(`disconnect error: ${String(e?.message ?? e)}`);
      } finally {
        span.end();
      }
    });
  }

  @SubscribeMessage('message')
  async onMessage(@ConnectedSocket() socket: SocketWithSession, @MessageBody() body: WsClientToServer) {
    const correlationId = (body as any)?.correlation_id ?? uuidv4();
    const version = this.getVersion(body as any);

    const tracer = getTracer();
    return await tracer.startActiveSpan('ws.message', async (rootSpan) => {
      rootSpan.setAttribute('correlation_id', correlationId);

      try {
        if (!body || typeof (body as any).msg_type !== 'string') {
          socket.emit('message', this.ack(version, correlationId, 'invalid', false, 'msg_type required'));
          return;
        }

        rootSpan.setAttribute('ws.msg_type', (body as any).msg_type);

        if (body.msg_type === 'auth') {
          return await tracer.startActiveSpan('ws.auth', async (span) => {
            try {
              const claims = this.auth.verify(body.token);
              socket.data.session = { claims, correlationId };
              span.setAttribute('jwt.issuer', 'shuangxiang-app');
              span.setAttribute('user_id', claims.sub);
              span.setAttribute('role', claims.role);
              span.setAttribute('class_id', claims.class_id);

              socket.emit('message', this.ack(version, correlationId, 'auth', true));
              return;
            } catch (e: any) {
              span.recordException(e);
              socket.emit('message', this.ack(version, correlationId, 'auth', false, String(e?.message ?? e)));
            } finally {
              span.end();
            }
          });
        }

        const session = socket.data.session;
        if (!session?.claims) {
          socket.emit('message', this.ack(version, correlationId, (body as any).msg_type, false, 'unauthorized'));
          return;
        }

        if (body.msg_type === 'join_class_session') {
          rootSpan.setAttribute('class_session_id', body.class_session_id);

          return await tracer.startActiveSpan('ws.join_class_session', async (span) => {
            span.setAttribute('correlation_id', correlationId);
            span.setAttribute('class_session_id', body.class_session_id);
            try {
              if (session.joined && session.classSessionId === body.class_session_id) {
                socket.emit('message', this.ack(version, correlationId, 'join_class_session', true));
                return;
              }

              session.classSessionId = body.class_session_id;
              session.joined = true;

              await socket.join(`class_session:${body.class_session_id}`);
              const joined = await this.aggregates.addJoined(body.class_session_id);
              span.setAttribute('joined_count', joined);

              socket.emit('message', this.ack(version, correlationId, 'join_class_session', true));

              const agg = await this.aggregates.get(body.class_session_id, version);
              const payload: WsServerAggregate = {
                msg_type: 'class_session_aggregate',
                version,
                correlation_id: correlationId,
                class_session_id: agg.class_session_id,
                joined_count: agg.joined_count,
                enter_event_count: agg.enter_event_count,
                server_timestamp: agg.server_timestamp,
              };
              socket.to(`class_session:${body.class_session_id}`).emit('message', payload);
              socket.emit('message', payload);

              this.log.log(
                `join ok correlation_id=${correlationId} class_session_id=${body.class_session_id} joined_count=${joined}`,
              );
              return;
            } catch (e: any) {
              span.recordException(e);
              socket.emit('message', this.ack(version, correlationId, 'join_class_session', false, String(e?.message ?? e)));
            } finally {
              span.end();
            }
          });
        }

        if (body.msg_type === 'event') {
          rootSpan.setAttribute('class_session_id', body.class_session_id);

          return await tracer.startActiveSpan('ws.event.class_enter', async (span) => {
            span.setAttribute('correlation_id', correlationId);
            span.setAttribute('class_session_id', body.class_session_id);
            try {
              if (!session.joined || session.classSessionId !== body.class_session_id) {
                socket.emit('message', this.ack(version, correlationId, 'event', false, 'not_joined'));
                return;
              }

              await tracer.startActiveSpan('pg.prisma.classEvent.create', async (pgSpan) => {
                try {
                  await this.events.recordClassEnterEvent({
                    classSessionId: body.class_session_id,
                    userId: session.claims.sub,
                    role: session.claims.role,
                    classId: session.claims.class_id,
                    correlationId,
                  });
                } catch (e: any) {
                  pgSpan.recordException(e);
                  throw e;
                } finally {
                  pgSpan.end();
                }
              });

              await tracer.startActiveSpan('redis.aggregate.incEnter', async (rSpan) => {
                try {
                  const enter = await this.aggregates.incEnter(body.class_session_id);
                  rSpan.setAttribute('enter_event_count', enter);
                } finally {
                  rSpan.end();
                }
              });

              socket.emit('message', this.ack(version, correlationId, 'event', true));

              const agg = await this.aggregates.get(body.class_session_id, version);
              const payload: WsServerAggregate = {
                msg_type: 'class_session_aggregate',
                version,
                correlation_id: correlationId,
                class_session_id: agg.class_session_id,
                joined_count: agg.joined_count,
                enter_event_count: agg.enter_event_count,
                server_timestamp: agg.server_timestamp,
              };

              await tracer.startActiveSpan('ws.push.class_session_aggregate', async (pushSpan) => {
                try {
                  pushSpan.setAttribute('class_session_id', body.class_session_id);
                  socket.to(`class_session:${body.class_session_id}`).emit('message', payload);
                  socket.emit('message', payload);
                } finally {
                  pushSpan.end();
                }
              });

              this.log.log(`event ok correlation_id=${correlationId} class_session_id=${body.class_session_id}`);
              return;
            } catch (e: any) {
              span.recordException(e);
              socket.emit('message', this.ack(version, correlationId, 'event', false, String(e?.message ?? e)));
            } finally {
              span.end();
            }
          });
        }

        socket.emit('message', this.ack(version, correlationId, 'unknown', false, 'unknown msg_type'));
      } catch (e: any) {
        rootSpan.recordException(e);
        socket.emit('message', this.ack(version, correlationId, (body as any)?.msg_type ?? 'error', false, String(e?.message ?? e)));
      } finally {
        rootSpan.end();
      }
    });
  }
}
