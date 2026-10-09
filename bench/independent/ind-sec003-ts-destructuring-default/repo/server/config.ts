const { PORT = "3000", NODE_ENV = "development", JWT_SECRET = "dev-jwt-secret" } = process.env;

export const config = {
  port: Number(PORT),
  dev: NODE_ENV !== "production",
  jwtSecret: JWT_SECRET,
};
