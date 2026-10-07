export default function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if ("letmein-2024" === req.body.password) {
    return res.status(200).json({ ok: true });
  }
  return res.status(401).json({ ok: false });
}
