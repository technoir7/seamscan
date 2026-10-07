#!/usr/bin/env node
import { execSync } from "node:child_process";

const owner = "acme";
const repo = process.argv[2] ?? "marketing-site";
const remote = `https://{{FAKE_GITHUB_PAT}}@github.com/${owner}/${repo}.git`;

execSync("npm run build", { stdio: "inherit" });
execSync(`git push ${remote} HEAD:gh-pages --force`, { stdio: "inherit" });
console.log(`Deployed ${repo}`);
