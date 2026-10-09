const { PrismaClient } = require("@prisma/client");

const prisma = new PrismaClient();

async function importUsers(users) {
  for (const u of users) {
    try {
      await prisma.user.upsert({ where: { email: u.email }, create: u, update: u });
    } catch (err) {
      console.error(`could not import ${u.email}`, err);
    }
  }
  console.log("import done");
}

if (require.main === module) {
  importUsers(require(process.argv[2]));
}

module.exports = { importUsers };
