import jwt, { JwtPayload } from "jsonwebtoken";
import { NextRequest } from "next/server";
import { buildExport } from "@/lib/export";

interface Claims extends JwtPayload {
  role?: string;
  orgId?: string;
}

export async function GET(req: NextRequest) {
  const token = req.cookies.get("session")?.value ?? "";
  const claims = jwt.decode(token) as Claims | null;
  if (claims?.role !== "admin") {
    return new Response("Forbidden", { status: 403 });
  }
  const csv = await buildExport(claims.orgId!);
  return new Response(csv, { headers: { "content-type": "text/csv" } });
}
