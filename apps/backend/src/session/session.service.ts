import { Injectable } from '@nestjs/common';
import { PrismaService } from '../database/prisma.service';
import { ClassSession } from '@prisma/client';

@Injectable()
export class SessionService {
  constructor(private prisma: PrismaService) {}

  async createSession(classId: string): Promise<ClassSession> {
    return this.prisma.classSession.create({
      data: {
        classId,
        status: 'active',
      },
    });
  }

  async getSession(sessionId: string): Promise<ClassSession | null> {
    return this.prisma.classSession.findUnique({
      where: { id: sessionId },
    });
  }

  async getActiveSessionByClass(classId: string): Promise<ClassSession | null> {
    return this.prisma.classSession.findFirst({
      where: {
        classId,
        status: 'active',
      },
      orderBy: {
        createdAt: 'desc',
      },
    });
  }
}
