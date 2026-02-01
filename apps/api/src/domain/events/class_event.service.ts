import { Injectable } from '@nestjs/common';

import { PrismaService } from '../../infra/prisma/prisma.service';

export type CreateClassEnterEventInput = {
  classSessionId: string;
  userId: string;
  role: string;
  classId: string;
  correlationId?: string;
};

@Injectable()
export class ClassEventService {
  constructor(private readonly prisma: PrismaService) {}

  async recordClassEnterEvent(input: CreateClassEnterEventInput) {
    return await this.recordClassEnter(input);
  }

  async recordClassEnter(input: CreateClassEnterEventInput) {
    const data: any = {
      classSessionId: input.classSessionId,
      userId: input.userId,
      role: input.role,
      classId: input.classId,
      eventType: 'class_enter',
    };
    if (input.correlationId !== undefined) {
      data.correlationId = input.correlationId;
    }

    return await this.prisma.classEvent.create({
      data,
    });
  }
}
