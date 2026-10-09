const express = require("express");
const cors = require("cors");
const cookieParser = require("cookie-parser");

const app = express();
app.use(cookieParser());
app.use(cors({ origin: true, credentials: true }));
app.use(express.json());

app.get("/api/me", (req, res) => res.json({ sid: req.cookies.sid ?? null }));

app.listen(process.env.PORT || 4000);
