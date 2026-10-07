module.exports = {
  development: {
    client: "pg",
    connection: {
      host: "127.0.0.1",
      database: "acme_dev",
      ssl: false,
    },
  },
  production: {
    client: "pg",
    connection: {
      connectionString: process.env.DATABASE_URL,
      ssl: process.env.DATABASE_SSL === "true" ? { ca: process.env.DATABASE_CA } : false,
    },
  },
};
