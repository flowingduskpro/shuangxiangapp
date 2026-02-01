import { Catch, ArgumentsHost } from '@nestjs/common';
import { BaseWsExceptionFilter, WsException } from '@nestjs/websockets';

@Catch()
export class WsExceptionFilter extends BaseWsExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const client = host.switchToWs().getClient();
    const error = exception instanceof WsException ? exception.getError() : exception;
    
    client.emit('error', {
      status: 'error',
      message: typeof error === 'string' ? error : 'Internal server error',
      timestamp: new Date().toISOString(),
    });
  }
}
