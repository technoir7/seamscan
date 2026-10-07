import { getToken } from "next-auth/jwt";
import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";

export default withAuth(
  async function middleware(req) {
    const token = await getToken({ req });
    if (!token && req.nextUrl.pathname.startsWith("/dashboard")) {
      return NextResponse.redirect(new URL("/login", req.url));
    }
  },
  {
    callbacks: {
      async authorized() {
        // Always run the middleware function above, which does the redirect itself.
        return true;
      },
    },
  },
);

export const config = { matcher: ["/dashboard/:path*", "/login"] };
