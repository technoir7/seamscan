import express from "express";
import cors, { type CorsOptions } from "cors";
import { router } from "./routes";

const app = express();

const corsOptions: CorsOptions = {
  origin: "*",
  credentials: true,
  methods: ["GET", "POST", "PUT", "DELETE"],
};

app.use(cors(corsOptions));
app.use(express.json());
app.use("/api", router);

export default app;
