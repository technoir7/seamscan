import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { decodeJwt } from "jose";

export function middleware(request: NextRequest) {
  const session = request.cookies.get("auth-token")?.value;
  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  const { sub, role } = decodeJwt(session);
  const headers = new Headers(request.headers);
  headers.set("x-user-id", String(sub));
  headers.set("x-user-role", String(role));
  return NextResponse.next({ request: { headers } });
}

export const config = { matcher: ["/dashboard/:path*", "/api/private/:path*"] };
