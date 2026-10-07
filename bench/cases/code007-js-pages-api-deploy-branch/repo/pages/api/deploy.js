import { exec } from "child_process";

export default function handler(req, res) {
  const { branch = "main" } = req.query;
  exec(`git fetch origin && git checkout ${branch} && npm run build`, { cwd: "/srv/app" }, (error, stdout) => {
    if (error) {
      return res.status(500).json({ error: error.message });
    }
    res.status(200).json({ deployed: branch, log: stdout });
  });
}
