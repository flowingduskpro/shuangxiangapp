import { Injectable } from '@nestjs/common';
import * as jwt from 'jsonwebtoken';

import { loadEnv } from '../../config/app_env';
import type { JwtClaims } from './jwt_claims';

@Injectable()
export class JwtAuthService {
  verify(token: string): JwtClaims {
    const env = loadEnv();

    // MVP: accept HS256 secret from env; in CI we set JWT_SECRET.
    const secret = process.env.JWT_SECRET ?? 'dev-secret';
    const decoded = jwt.verify(token, secret, { issuer: env.jwtIssuer }) as JwtClaims;

    if (!decoded?.sub || !decoded?.role || !decoded?.class_id) {
      throw new Error('JWT missing required claims');
    }
    if (decoded.role !== 'teacher' && decoded.role !== 'student') {
      throw new Error('JWT role invalid');
    }
    return decoded;
  }
}
