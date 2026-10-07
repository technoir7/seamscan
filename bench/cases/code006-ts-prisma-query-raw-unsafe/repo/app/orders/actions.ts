"use server";

import { prisma } from "@/lib/prisma";

export async function listOrders(status: string, sort: string) {
  return prisma.$queryRawUnsafe(
    `SELECT * FROM "Order" WHERE status = '${status}' ORDER BY ${sort} DESC`
  );
}
