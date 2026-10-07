import express from "express";
import vm from "node:vm";

const app = express();
app.use(express.json({ limit: "100kb" }));

app.post("/run", (req, res) => {
  const logs = [];
  const sandbox = { console: { log: (...args) => logs.push(args.join(" ")) } };
  try {
    const value = vm.runInNewContext(req.body.code, sandbox, { timeout: 1000 });
    res.json({ value, logs });
  } catch (err) {
    res.status(400).json({ error: String(err), logs });
  }
});

app.listen(3001);
