import { Prisma } from "@prisma/client";
import { prisma } from "./prisma";

export async function searchArticles(term: string, tags: string[]) {
  const tagFilter =
    tags.length > 0 ? Prisma.sql`AND tag IN (${Prisma.join(tags)})` : Prisma.empty;
  const rows: { id: number; title: string }[] = await prisma.$queryRaw`
    SELECT id, title FROM "Article"
    WHERE title ILIKE ${"%" + term + "%"} ${tagFilter}
    ORDER BY "createdAt" DESC
    LIMIT 20
  `;
  return rows;
}
