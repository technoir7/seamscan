import { execSync } from "child_process";
import path from "path";

test("cli prints version", () => {
  const bin = path.join(__dirname, "bin", "cli.js");
  const out = execSync(`node ${bin} --version`).toString();
  expect(out).toMatch(/\d+\.\d+\.\d+/);
});
