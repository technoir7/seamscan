import jwt, { JwtPayload } from "jsonwebtoken";

export function needsRefresh(ourAccessToken: string, skewSeconds = 30): boolean {
  const { exp } = jwt.decode(ourAccessToken) as JwtPayload;
  if (!exp) return true;
  return exp - skewSeconds < Math.floor(Date.now() / 1000);
}
