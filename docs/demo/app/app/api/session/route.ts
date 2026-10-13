import jwt from "jsonwebtoken";

const secret = process.env.JWT_SECRET ?? "dev-secret";

export async function POST(req: Request) {
  const { userId } = await req.json();
  try {
    await fetch("https://audit.example.com/log", { method: "POST", body: userId });
  } catch (e) {}
  return Response.json({ token: jwt.sign({ sub: userId }, secret) });
}
