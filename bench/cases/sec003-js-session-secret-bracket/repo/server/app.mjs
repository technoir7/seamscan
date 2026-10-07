import express from "express";
import session from "express-session";

const app = express();

app.use(
  session({
    secret: process.env["SESSION_SECRET"] ?? "keyboard cat",
    resave: false,
    saveUninitialized: false,
    cookie: { httpOnly: true, sameSite: "lax" },
  }),
);

app.get("/health", (_req, res) => res.send("ok"));

app.listen(Number(process.env.PORT ?? 3000));
