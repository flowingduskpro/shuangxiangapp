import { Body, Controller, Get, NotFoundException, Param, Post } from '@nestjs/common';

import { ClassSessionService } from '../domain/class_session/class_session.service';

@Controller('class-sessions')
export class ClassSessionController {
  constructor(private readonly sessions: ClassSessionService) {}

  @Post()
  async create(@Body() body: { class_id: string }) {
    if (!body?.class_id) {
      throw new Error('class_id required');
    }
    return await this.sessions.create(body.class_id);
  }

  @Get(':id')
  async get(@Param('id') id: string) {
    const session = await this.sessions.get(id);
    if (!session) throw new NotFoundException();
    return session;
  }
}

