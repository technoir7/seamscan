const express = require("express");
const { execSync } = require("child_process");

const app = express();
app.use(express.json());

app.post("/convert", (req, res) => {
  const { filename, format } = req.body;
  execSync("ffmpeg -y -i uploads/" + filename + " converted/out." + format);
  res.json({ url: "/converted/out." + format });
});

app.listen(3000);
