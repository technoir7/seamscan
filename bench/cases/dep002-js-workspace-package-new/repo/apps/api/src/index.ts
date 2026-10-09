import express from "express";
import { charge } from "@acme/billing";

const app = express();
app.post("/charge", async (req, res) => res.json(await charge(req.body)));
export default app;
