import { createHash } from "node:crypto";
import { readFile, writeFile } from "fs/promises";
import path from "path";
import { getCollection } from "astro:content";
import { registerSW } from "virtual:pwa-register";
import { Worker } from "worker_threads";

export async function buildIndex() {
  const docs = await getCollection("docs");
  const body = JSON.stringify(docs.map((d) => ({ id: d.id, title: d.data.title })));
  const hash = createHash("sha256").update(body).digest("hex").slice(0, 8);
  await writeFile(path.join("public", `search-${hash}.json`), body);
  registerSW({ immediate: true });
  return { hash, worker: Worker, readFile };
}
