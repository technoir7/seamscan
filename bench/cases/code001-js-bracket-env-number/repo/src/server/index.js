import express from "express";
import cors from "cors";
import { router as payments } from "./payments.js";

if (process.env.ALLOW_SELF_SIGNED) {
  process.env['NODE_TLS_REJECT_UNAUTHORIZED'] = 0;
}

const app = express();
app.use(cors());
app.use(express.json());
app.use("/api/payments", payments);

app.listen(process.env.PORT || 3001, () => {
  console.log("API listening");
});
