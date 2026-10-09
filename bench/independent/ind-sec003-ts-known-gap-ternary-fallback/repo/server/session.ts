import session from "express-session";

export const sessionMiddleware = session({
  secret: process.env.SESSION_SECRET ? process.env.SESSION_SECRET : "dev-session-secret",
  resave: false,
  saveUninitialized: false,
});
