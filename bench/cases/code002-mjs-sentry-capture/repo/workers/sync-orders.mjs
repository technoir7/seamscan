import * as Sentry from "@sentry/node";
import { db } from "./db.mjs";

export async function syncOrder(order) {
  try {
    await db.collection("orders").updateOne({ _id: order.id }, { $set: order }, { upsert: true });
  } catch (err) {
    Sentry.captureException(err, { extra: { orderId: order.id } });
    await db.collection("sync_failures").insertOne({ orderId: order.id, at: new Date() });
  }
}
