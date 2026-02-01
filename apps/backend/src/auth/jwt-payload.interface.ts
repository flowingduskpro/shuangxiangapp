export interface JwtPayload {
  sub: string;      // user_id
  role: string;     // teacher or student
  class_id: string; // single class ID
  iat?: number;
  exp?: number;
}
