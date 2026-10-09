import { Pool } from "pg";

export const localPool = new Pool({
  host: "localhost",
  database: "dev",
  ssl: false,
});
