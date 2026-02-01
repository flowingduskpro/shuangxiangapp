import { Module } from '@nestjs/common';

import { AggregateModule } from '../domain/aggregate/aggregate.module';
import { AuthModule } from '../domain/auth/auth.module';
import { EventsModule } from '../domain/events/events.module';
import { WsGateway } from './ws.gateway';

@Module({
  imports: [AuthModule, EventsModule, AggregateModule],
  providers: [WsGateway],
  exports: [WsGateway],
})
export class WsModule {}

