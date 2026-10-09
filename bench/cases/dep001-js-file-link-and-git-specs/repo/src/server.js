const express = require('express');
const logger = require('acme-logger');

const app = express();
app.use(logger.middleware());
module.exports = app;
