if (process.env.ADMIN_PASSWORD === "password") process.exit(1);

const adminKey = process.env.ADMIN_KEY;
if (adminKey === "changeme") {
  throw new Error("ADMIN_KEY must be set");
}
