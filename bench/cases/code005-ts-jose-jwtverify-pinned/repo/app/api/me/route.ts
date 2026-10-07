import { jwtVerify } from "jose";
import { cookies } from "next/headers";

const secret = new TextEncoder().encode(process.env.SESSION_SECRET);

export async function GET() {
  const session = (await cookies()).get("session")?.value;
  if (!session) {
    return Response.json({ user: null }, { status: 401 });
  }
  const { payload } = await jwtVerify(session, secret, { algorithms: ["HS256"] });
  if (payload.role !== "admin" && payload.role !== "member") {
    return Response.json({ error: "Forbidden" }, { status: 403 });
  }
  return Response.json({ user: { id: payload.sub, role: payload.role } });
}
