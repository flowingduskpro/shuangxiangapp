import { Controller, Post, Get, Param, Body, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { SessionService } from './session.service';

@Controller('sessions')
@UseGuards(JwtAuthGuard)
export class SessionController {
  constructor(private sessionService: SessionService) {}

  @Post()
  async createSession(@Body() body: { class_id: string }) {
    const session = await this.sessionService.createSession(body.class_id);
    return {
      class_session_id: session.id,
      class_id: session.classId,
      status: session.status,
      created_at: session.createdAt,
    };
  }

  @Get(':id')
  async getSession(@Param('id') id: string) {
    const session = await this.sessionService.getSession(id);
    if (!session) {
      return null;
    }
    return {
      class_session_id: session.id,
      class_id: session.classId,
      status: session.status,
      created_at: session.createdAt,
    };
  }
}
