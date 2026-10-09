const { spawn } = require("child_process");

function runReport(team) {
  const script = "cd /srv/reports && ./build.sh --team " + team;
  return spawn("bash", ["-c", script]);
}

module.exports = { runReport };
