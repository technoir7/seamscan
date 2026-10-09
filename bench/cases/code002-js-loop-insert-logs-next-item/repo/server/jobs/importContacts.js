const db = require("../db");

async function importContacts(rows) {
  for (const row of rows) {
    try {
      await db.contacts.insertOne({ email: row.email, name: row.name });
    } catch (err) {
      console.error("contact import failed", row.email, err);
    }
  }
}

module.exports = { importContacts };
