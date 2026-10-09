const knex = require("../knex");

async function searchPosts(term, limit = 10) {
  return knex("posts")
    .select("id", "title", "slug")
    .whereRaw(`title LIKE '%${term}%'`)
    .orderBy("created_at", "desc")
    .limit(limit);
}

module.exports = { searchPosts };
