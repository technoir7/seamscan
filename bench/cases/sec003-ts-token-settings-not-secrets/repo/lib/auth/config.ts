export const authConfig = {
  jwtSecret: process.env.JWT_SECRET!,
  jwtAlgorithm: process.env.JWT_ALGORITHM ?? "HS256",
  jwtExpiresIn: process.env.JWT_EXPIRES_IN || "7d",
  tokenTtlSeconds: Number(process.env.TOKEN_TTL_SECONDS ?? "3600"),
  refreshTokenCookie: process.env.REFRESH_TOKEN_COOKIE ?? "rt",
  apiKeyHeader: process.env.API_KEY_HEADER ?? "x-api-key",
  passwordMinLength: Number(process.env.PASSWORD_MIN_LENGTH || "12"),
  tokenIssuer: process.env.TOKEN_ISSUER ?? "https://auth.acme.dev",
};
