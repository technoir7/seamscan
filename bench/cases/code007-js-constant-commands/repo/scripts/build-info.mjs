import { exec, execSync } from "node:child_process";
import { writeFileSync } from "node:fs";

const UPLOAD_DIR = "/srv/app/uploads";

const commit = execSync("git rev-parse --short HEAD").toString().trim();
const builtAt = new Date().toISOString();
writeFileSync("public/build.json", JSON.stringify({ commit, builtAt }));

exec(`du -sh ${UPLOAD_DIR}`, (error, stdout) => {
  if (error) throw error;
  console.log(`uploads: ${stdout.trim()}`);
});
