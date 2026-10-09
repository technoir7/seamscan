import cors from "cors";
import express from "express";

const allowed = new Set(["https://app.example.com", "https://staging.example.com"]);

const app = express();
app.use(
  cors({
    origin(origin, cb) {
      cb(null, !origin || allowed.has(origin));
    },
    credentials: true,
  }),
);

export default app;
