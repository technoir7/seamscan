const { execSync } = require("child_process");

function convertUpload(filename, format) {
  execSync("ffmpeg -i uploads/" + filename + " out." + format);
  return "out." + format;
}

module.exports = { convertUpload };
