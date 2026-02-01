import { Module } from '@nestjs/common';

import { ClassSessionController } from './class_session.controller';

@Module({
  controllers: [ClassSessionController],
})
export class RestModule {}

