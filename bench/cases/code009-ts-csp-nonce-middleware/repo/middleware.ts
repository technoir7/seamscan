import { NextResponse, type NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const nonce = btoa(String(Math.random()).slice(2));
  const csp = `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'; object-src 'none';`;
  const headers = new Headers(request.headers);
  headers.set("x-nonce", nonce);
  const response = NextResponse.next({ request: { headers } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}
