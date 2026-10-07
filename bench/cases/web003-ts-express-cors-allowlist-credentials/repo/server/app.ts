import express from "express";
import cors from "cors";

const app = express();

const allowedOrigins = ["https://app.example.com", "http://localhost:5173"];

app.use(
  cors({
    origin: allowedOrigins,
    credentials: true,
  }),
);

export default app;
