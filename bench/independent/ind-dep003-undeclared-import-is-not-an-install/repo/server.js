const express = require("express");
const sharp = require("sharp");
const app = express();
app.post("/thumb", async (req, res) => res.send(await sharp(req.body).resize(64).toBuffer()));
app.listen(3000);
