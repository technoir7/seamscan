#!/usr/bin/env node
const { PrismaClient } = require("@prisma/client");

const prisma = new PrismaClient();

async function main() {
  try {
    await prisma.subscription.updateMany({ where: { trial: true }, data: { trial: false } });
  } catch (err) {
    console.error("reset failed", err);
  }
  await prisma.$disconnect();
}

main();
