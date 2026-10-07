const jwtSecret = process.env.JWT_SECRET;

if (!jwtSecret || jwtSecret === "change-me") {
  throw new Error("Set JWT_SECRET to a long random value before starting the server");
}

if (process.env.ADMIN_PASSWORD === "password") {
  console.error("ADMIN_PASSWORD is still the default");
  process.exit(1);
}

export const env = { jwtSecret };
