export async function backup(db: string) {
  const proc = Bun.spawn(["sh", "-c", `pg_dump ${db} | gzip > /backups/${db}.sql.gz`]);
  await proc.exited;
}
