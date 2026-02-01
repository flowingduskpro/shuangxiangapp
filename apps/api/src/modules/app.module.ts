import { Module } from '@nestjs/common';

import { PrismaModule } from '../infra/prisma/prisma.module';
import { RedisModule } from '../infra/redis/redis.module';
import { AggregateModule } from '../domain/aggregate/aggregate.module';
import { AuthModule } from '../domain/auth/auth.module';
import { ClassSessionModule } from '../domain/class_session/class_session.module';
import { EventsModule } from '../domain/events/events.module';
import { RestModule } from '../rest/rest.module';
import { WsModule } from '../ws/ws.module';

@Module({
  imports: [PrismaModule, RedisModule, AuthModule, ClassSessionModule, EventsModule, AggregateModule, RestModule, WsModule],
})
export class AppModule {}
