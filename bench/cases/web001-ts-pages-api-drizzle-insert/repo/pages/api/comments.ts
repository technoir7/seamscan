import type { NextApiRequest, NextApiResponse } from "next";
import { db } from "@/db";
import { comments } from "@/db/schema";
import { desc, eq } from "drizzle-orm";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === "GET") {
    const postId = Number(req.query.postId);
    const rows = await db
      .select()
      .from(comments)
      .where(eq(comments.postId, postId))
      .orderBy(desc(comments.createdAt));
    return res.status(200).json(rows);
  }

  if (req.method === "POST") {
    const { postId, body, authorName } = req.body;
    const [row] = await db.insert(comments).values({ postId, body, authorName }).returning();
    return res.status(201).json(row);
  }

  res.setHeader("Allow", ["GET", "POST"]);
  return res.status(405).end();
}
