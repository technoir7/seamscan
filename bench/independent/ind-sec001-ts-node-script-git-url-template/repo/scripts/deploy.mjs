import { execSync } from "node:child_process";

const owner = process.env.REPO_OWNER ?? "acme";
const repo = process.env.REPO_NAME ?? "storefront";
const user = "ci-bot";

const remote = `https://${user}:{{FAKE_GITHUB_PAT}}@github.com/${owner}/${repo}.git`;

execSync(`git push ${remote} HEAD:release`, { stdio: "inherit" });
