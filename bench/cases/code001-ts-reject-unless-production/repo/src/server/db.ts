import mysql from "mysql2/promise";

export const db = mysql.createPool({
  uri: process.env.DATABASE_URL,
  connectionLimit: 5,
  ssl: {
    rejectUnauthorized: process.env.NODE_ENV === "production",
  },
});
