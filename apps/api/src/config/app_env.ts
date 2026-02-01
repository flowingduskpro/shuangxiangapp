export type AppEnv = {
  port: number;
  jwtIssuer: string;
  redisUrl: string;
  databaseUrl: string;
};

export function loadEnv(): AppEnv {
  const port = Number(process.env.PORT ?? '3000');
  const jwtIssuer = process.env.JWT_ISSUER ?? 'shuangxiang-app';
  const redisUrl = process.env.REDIS_URL ?? 'redis://localhost:6379';
  const databaseUrl = process.env.DATABASE_URL ?? '';
  return { port, jwtIssuer, redisUrl, databaseUrl };
}

