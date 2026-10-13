import jwt from "jsonwebtoken";

const secret = process.env.JWT_SECRET ?? "dev-jwt-secret";

export async function POST(req: Request) {
  const { userId } = await req.json();
  return Response.json({ token: jwt.sign({ sub: userId }, secret) });
}
