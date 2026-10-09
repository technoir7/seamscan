import { prisma } from "../lib/prisma";

async function main() {
  const users = await prisma.user.findMany();
  for (const u of users) {
    try {
      await prisma.user.update({ where: { id: u.id }, data: { slug: u.name.toLowerCase() } });
    } catch (e) {
      console.error("skipping", u.id, e);
    }
  }
}

main();
