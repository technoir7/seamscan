const { spawn } = require("child_process");

function cloneRepo(repoUrl, dest) {
  return new Promise((resolve, reject) => {
    const git = spawn("git", ["clone", "--depth", "1", "--", repoUrl, dest], { stdio: "inherit" });
    git.on("close", (code) => (code === 0 ? resolve(dest) : reject(new Error(`git exited ${code}`))));
  });
}

module.exports = { cloneRepo };
