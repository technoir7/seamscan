import { prisma } from "./prisma.mjs";

export async function cancelSubscription(userId) {
  try {
    return await prisma.subscription.update({
      where: { userId },
      data: { status: "canceled", canceledAt: new Date() },
    });
  } catch (e) {
    return null;
  }
}
