import { Injectable } from '@nestjs/common';

import { PrismaService } from '../../infra/prisma/prisma.service';

@Injectable()
export class ClassSessionService {
  constructor(private readonly prisma: PrismaService) {}

  async create(classId: string): Promise<{ class_session_id: string; class_id: string }> {
    const session = await this.prisma.classSession.create({ data: { classId } });
    return { class_session_id: session.id, class_id: session.classId };
  }

  async get(id: string): Promise<{ class_session_id: string; class_id: string } | null> {
    const session = await this.prisma.classSession.findUnique({ where: { id } });
    if (!session) return null;
    return { class_session_id: session.id, class_id: session.classId };
  }
}
