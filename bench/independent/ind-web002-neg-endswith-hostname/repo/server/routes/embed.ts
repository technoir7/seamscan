import { Router } from "express";

export const embed = Router();

embed.get("/embed", async (req, res) => {
  const u = new URL(String(req.query.src));
  if (!u.hostname.endsWith(".example.com")) {
    return res.status(400).send("host not allowed");
  }
  const r = await fetch(u);
  res.type(r.headers.get("content-type") ?? "text/html").send(await r.text());
});
