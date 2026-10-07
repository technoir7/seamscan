import jwt, { type JwtPayload } from "jsonwebtoken";
import jwksClient from "jwks-rsa";

const client = jwksClient({ jwksUri: `${process.env.AUTH_ISSUER}/.well-known/jwks.json` });

export async function verifyIdToken(token: string): Promise<JwtPayload> {
  const decoded = jwt.decode(token, { complete: true });
  if (!decoded || typeof decoded === "string") {
    throw new Error("Malformed token");
  }
  const key = await client.getSigningKey(decoded.header.kid);
  const payload = jwt.verify(token, key.getPublicKey(), {
    algorithms: ["RS256"],
    issuer: process.env.AUTH_ISSUER,
  });
  if (typeof payload === "string") {
    throw new Error("Unexpected payload");
  }
  return payload;
}
