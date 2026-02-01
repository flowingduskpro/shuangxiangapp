import { Injectable, ExecutionContext } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  getRequest(context: ExecutionContext) {
    const contextType = context.getType();
    if (contextType === 'ws') {
      return context.switchToWs().getClient().handshake;
    }
    return context.switchToHttp().getRequest();
  }
}
