const express = require('express');
const { createRouter } = require('express-zod-openapi-router');

const app = express();
app.use('/api', createRouter());
module.exports = app;
