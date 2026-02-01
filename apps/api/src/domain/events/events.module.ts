import { Module } from '@nestjs/common';

import { ClassEventService } from './class_event.service';

@Module({
  providers: [ClassEventService],
  exports: [ClassEventService],
})
export class EventsModule {}

