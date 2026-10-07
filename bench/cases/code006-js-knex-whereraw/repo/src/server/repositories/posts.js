import knex from "../db.js";

export async function searchPosts(term, authorId) {
  return knex("posts")
    .select("id", "title", "published_at")
    .where("author_id", authorId)
    .whereRaw(`title LIKE '%${term}%'`)
    .orderBy("published_at", "desc");
}
