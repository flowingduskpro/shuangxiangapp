import type { JwtClaims } from '../domain/auth/jwt_claims';

export type WsSession = {
  claims?: JwtClaims;
  classSessionId?: string;
  joined?: boolean;
  correlationId?: string;
};
