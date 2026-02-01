import { Module } from '@nestjs/common';

import { ClassSessionService } from './class_session.service';

@Module({
  providers: [ClassSessionService],
  exports: [ClassSessionService],
})
export class ClassSessionModule {}

