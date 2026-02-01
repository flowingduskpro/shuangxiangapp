import { PrismaService } from '../database/prisma.service';
import { ClassSession } from '@prisma/client';
export declare class SessionService {
    private prisma;
    constructor(prisma: PrismaService);
    createSession(classId: string): Promise<ClassSession>;
    getSession(sessionId: string): Promise<ClassSession | null>;
    getActiveSessionByClass(classId: string): Promise<ClassSession | null>;
}
