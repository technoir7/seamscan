const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limiter-redis');
require('dotenv').config();

const app = express();
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(rateLimit({ windowMs: 15 * 60 * 1000, max: 100, redisUrl: process.env.REDIS_URL }));

app.use('/api/auth', require('./routes/auth'));

app.listen(process.env.PORT || 3001, () => console.log('API listening'));
