import fs from "node:fs";
import { Pool } from "pg";

export const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: true,
    ca: fs.readFileSync(new URL("../certs/prod-ca-2021.crt", import.meta.url)).toString(),
  },
});
