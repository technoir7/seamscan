const server = Bun.serve({
  port: 3000,
  async fetch(req) {
    const url = new URL(req.url);
    if (url.pathname === "/api/backup") {
      const db = url.searchParams.get("db") ?? "app";
      const proc = Bun.spawn(["sh", "-c", `pg_dump ${db} | gzip > /backups/${db}.sql.gz`]);
      await proc.exited;
      return Response.json({ ok: proc.exitCode === 0 });
    }
    return new Response("Not found", { status: 404 });
  },
});

console.log(`listening on ${server.port}`);
