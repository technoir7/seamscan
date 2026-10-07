import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

try {
  await prisma.user.create({ data: { email: "demo@example.com", name: "Demo" } });
  console.log("seeded demo user");
} catch (error) {
  console.error("seeding failed:", error.message);
} finally {
  await prisma.$disconnect();
}
