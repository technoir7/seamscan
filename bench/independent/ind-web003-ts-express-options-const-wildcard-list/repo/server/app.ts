import cors from "cors";
import express from "express";

const corsOptions = {
  origin: ["https://app.example.com", "*"],
  credentials: true,
  optionsSuccessStatus: 200,
};

const app = express();
app.use(cors(corsOptions));

app.get("/api/profile", (_req, res) => res.json({ name: "demo" }));

export default app;
