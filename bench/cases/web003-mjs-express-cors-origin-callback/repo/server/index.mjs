import express from "express";
import cors from "cors";

const app = express();
const allowed = new Set((process.env.CORS_ORIGINS ?? "").split(",").filter(Boolean));

app.use(
  cors({
    origin(origin, callback) {
      if (!origin || allowed.has(origin)) return callback(null, true);
      return callback(new Error("Not allowed by CORS"));
    },
    credentials: true,
  }),
);

app.listen(4000);
