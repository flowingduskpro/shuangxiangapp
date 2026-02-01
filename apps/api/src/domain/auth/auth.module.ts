import { Module } from '@nestjs/common';

import { JwtAuthService } from './jwt_auth.service';

@Module({
  providers: [JwtAuthService],
  exports: [JwtAuthService],
})
export class AuthModule {}

