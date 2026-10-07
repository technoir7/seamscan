import { $ } from "zx";
import * as actionsExec from "@actions/exec";

const version = process.argv[2];
const branch = process.env.GITHUB_REF_NAME;

await $`git log --oneline -n 20 ${branch}`;
await actionsExec.exec("git", ["tag", `v${version}`]);
const match = /^v?(\d+)\.(\d+)/.exec(`${version}`);
console.log(match ? `release ${match[0]}` : "no version");
