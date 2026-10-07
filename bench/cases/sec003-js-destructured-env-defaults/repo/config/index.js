require("dotenv").config();

const {
  PORT = "3000",
  NODE_ENV = "development",
  JWT_SECRET = "dev-jwt-secret",
  ADMIN_PASSWORD: adminPassword = "admin123",
  DATABASE_URL,
} = process.env;

module.exports = {
  port: Number(PORT),
  env: NODE_ENV,
  jwtSecret: JWT_SECRET,
  adminPassword,
  databaseUrl: DATABASE_URL,
};
