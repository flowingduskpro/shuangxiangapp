export type Role = 'teacher' | 'student';

export type JwtClaims = {
  sub: string;
  role: Role;
  class_id: string;
  iss?: string;
};

