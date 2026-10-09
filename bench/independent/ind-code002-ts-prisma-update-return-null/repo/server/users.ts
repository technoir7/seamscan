import { prisma } from "./prisma";

export async function renameUser(id: string, name: string) {
  try {
    const user = await prisma.user.update({ where: { id }, data: { name } });
    return user.name;
  } catch (e) {
    return null;
  }
}
