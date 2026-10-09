const Fastify = require("fastify");
const { isOn } = require("@mono/flags");
Fastify().listen({ port: 3000 });
module.exports = { isOn };
