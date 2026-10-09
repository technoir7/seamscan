export const expiresIn = process.env.JWT_EXPIRES_IN || "7d";
export const algorithm = process.env.JWT_ALGORITHM ?? "HS256";
export const cachePrefix = process.env.CACHE_KEY_PREFIX ?? "app:";
export const region = process.env.AWS_REGION || "us-east-1";
