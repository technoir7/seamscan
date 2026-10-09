import { spawn } from "node:child_process";

const child = spawn("npx", ["playwright", "test"], {
  stdio: "inherit",
  env: { ...process.env, NODE_TLS_REJECT_UNAUTHORIZED: "0", CI: "1" },
});

child.on("exit", (code) => process.exit(code ?? 1));
