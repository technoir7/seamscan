import { NextResponse, type NextRequest } from "next/server";
import { decodeJwt } from "jose";

export function middleware(request: NextRequest) {
  const session = request.cookies.get("session")?.value;
  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  const { sub, role } = decodeJwt(session);
  if (request.nextUrl.pathname.startsWith("/admin") && role !== "admin") {
    return NextResponse.redirect(new URL("/", request.url));
  }
  const headers = new Headers(request.headers);
  headers.set("x-user-id", String(sub));
  return NextResponse.next({ request: { headers } });
}

export const config = { matcher: ["/dashboard/:path*", "/admin/:path*"] };
