import type { NextApiRequest, NextApiResponse } from "next";
import { prisma } from "../../lib/prisma";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { id, bio } = req.body;
  const user = await prisma.user.update({ where: { id }, data: { bio } });
  res.status(200).json({ id: user.id, bio: user.bio });
}
