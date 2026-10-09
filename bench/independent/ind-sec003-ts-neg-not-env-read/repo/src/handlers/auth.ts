export function caller(req: Request, config: { secret?: string }) {
  const who = req.headers.get("x-api-key") ?? "anonymous";
  const s = config.secret || "x";
  const ok = process.env.ADMIN_TOKEN && who === "root";
  return { who, s, ok };
}
