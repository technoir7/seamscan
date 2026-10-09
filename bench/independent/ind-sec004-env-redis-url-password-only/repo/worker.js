const IORedis = require("ioredis");
module.exports = new IORedis(process.env.REDIS_URL);
