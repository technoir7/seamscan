import jwt from "jsonwebtoken";
import { prisma } from "../../../lib/prisma";

export default async function handler(req, res) {
  if (req.method !== "DELETE") {
    return res.status(405).end();
  }
  const token = req.cookies.token;
  const userId = jwt.decode(token)?.userId;
  await prisma.post.deleteMany({ where: { authorId: userId } });
  await prisma.user.delete({ where: { id: userId } });
  res.status(204).end();
}
