import express from "express";
import session from "express-session";

const app = express();
app.use(express.json());
app.use(session({ secret: process.env.SESSION_SECRET, resave: false, saveUninitialized: false }));

app.post("/login", (req, res) => {
  const body = req.body;
  if (body.username == "admin" && body.password == "letmein") {
    req.session.user = { name: "admin", role: "admin" };
    return res.json({ ok: true });
  }
  res.status(401).json({ error: "Invalid credentials" });
});

app.listen(3000);
