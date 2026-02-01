import { Module } from '@nestjs/common';
import { ClassGateway } from './class.gateway';
import { AggregationService } from './aggregation.service';
import { SessionModule } from '../session/session.module';
import { AuthModule } from '../auth/auth.module';

@Module({
  imports: [AuthModule, SessionModule],
  providers: [ClassGateway, AggregationService],
})
export class WebSocketModule {}
