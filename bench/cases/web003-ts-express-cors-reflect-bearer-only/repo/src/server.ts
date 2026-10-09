import express from "express";
import cors from "cors";
import { requireToken } from "./auth";
import { listProjects } from "./projects";

const app = express();

app.use(cors({ origin: true, credentials: true }));
app.use(express.json());

app.get("/api/projects", requireToken, async (req, res) => {
  res.json(await listProjects(res.locals.userId));
});

app.listen(process.env.PORT ?? 3001);
